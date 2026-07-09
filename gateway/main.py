import asyncio
import hashlib
import logging
import os
import secrets
import uuid
from collections.abc import Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

import aio_pika
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from models import (
    ApiKeyCreatedResponse,
    BotStatusResponse,
    CreateApiKeyRequest,
    PublishEventRequest,
)

from shared.config import build_rabbitmq_url, load_redis_config
from shared.db import supabase
from shared.models import EventPayload, EventStatus

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


def _spawn_background_task(coro: Coroutine[Any, Any, None]) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _generate_api_key(prefix: str = "gwh") -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def _extract_api_key(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip() or None
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


async def _touch_last_used_at(key_id: str) -> None:
    try:
        supabase.table("api_keys").update(
            {"last_used_at": datetime.now(UTC).isoformat()}
        ).eq("id", key_id).execute()
    except Exception:
        logger.warning(
            "Failed to update last_used_at for key_id=%s", key_id, exc_info=True
        )


async def _resolve_guild_id_from_api_key(api_key: str) -> str | None:
    key_hash = _hash_api_key(api_key)
    response = (
        supabase.table("api_keys")
        .select("id, project_id, projects!inner(guild_id)")
        .eq("key_hash", key_hash)
        .limit(1)
        .execute()
    )

    rows = cast(list[dict[str, Any]], response.data or [])
    if not rows:
        return None

    row = rows[0]
    key_id = row["id"]
    guild_id = row["projects"]["guild_id"]

    if guild_id is None:
        return None

    _spawn_background_task(_touch_last_used_at(key_id))

    return guild_id


def _resolve_authenticated_user_id(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_jwt = authorization[7:].strip()
    if not user_jwt:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        user_response = supabase.auth.get_user(user_jwt)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    if user_response is None or user_response.user is None:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user_response.user.id


class EventStatusStore:
    def __init__(
        self, client: redis.Redis, prefix: str, ttl_seconds: int | None
    ) -> None:
        self._client = client
        self._prefix = prefix
        self._ttl_seconds = ttl_seconds

    def _key(self, event_id: str) -> str:
        return f"{self._prefix}:{event_id}"

    async def get(self, event_id: str) -> EventStatus | None:
        value = await self._client.get(self._key(event_id))
        if value is None:
            return None
        try:
            return EventStatus(value)
        except ValueError:
            return None

    async def set(self, event_id: str, status: EventStatus) -> None:
        key = self._key(event_id)
        if self._ttl_seconds is None:
            await self._client.set(key, status.value)
        else:
            await self._client.set(key, status.value, ex=self._ttl_seconds)


class RateLimitStore:
    def __init__(self, client: redis.Redis, prefix: str) -> None:
        self._client = client
        self._prefix = prefix

    def _key(self, identifier: str) -> str:
        return f"{self._prefix}:{identifier}"

    async def increment(self, identifier: str, window_seconds: int) -> int:
        key = self._key(identifier)
        pipeline = self._client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, window_seconds, nx=True)
        count, _ = await pipeline.execute()
        return int(count)

    async def get(self, identifier: str) -> int:
        value = await self._client.get(self._key(identifier))
        return int(value or 0)

    async def reset(self, identifier: str) -> None:
        await self._client.delete(self._key(identifier))


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_config = load_redis_config()
    redis_client = redis.from_url(redis_config.url, decode_responses=True)
    app.state.redis = redis_client
    app.state.event_status_store = EventStatusStore(
        redis_client,
        redis_config.event_status_prefix,
        redis_config.event_status_ttl_seconds,
    )
    if not redis_config.rate_limit_prefix:
        raise RuntimeError("REDIS_RATE_LIMIT_PREFIX is required for gateway")
    app.state.rate_limit_store = RateLimitStore(
        redis_client, redis_config.rate_limit_prefix
    )
    app.state.rate_limit_max_requests = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
    app.state.rate_limit_window_seconds = int(
        os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    )

    rabbitmq_url = build_rabbitmq_url()
    rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
    rabbitmq_channel = await rabbitmq_connection.channel()
    queue_name = os.getenv("RABBITMQ_QUEUE", "events")
    exchange_name = os.getenv("RABBITMQ_EXCHANGE", "events")
    routing_key = os.getenv("RABBITMQ_ROUTING_KEY", queue_name)

    rabbitmq_queue = await rabbitmq_channel.declare_queue(queue_name, durable=True)
    if exchange_name:
        rabbitmq_exchange = await rabbitmq_channel.declare_exchange(
            exchange_name,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        await rabbitmq_queue.bind(rabbitmq_exchange, routing_key)
    else:
        rabbitmq_exchange = rabbitmq_channel.default_exchange

    app.state.rabbitmq_connection = rabbitmq_connection
    app.state.rabbitmq_channel = rabbitmq_channel
    app.state.rabbitmq_exchange = rabbitmq_exchange
    app.state.rabbitmq_queue = rabbitmq_queue
    app.state.rabbitmq_routing_key = routing_key

    app.state.discord_bot_client = httpx.AsyncClient(
        base_url=os.getenv("DISCORD_BOT_URL", "http://discord-bot:8001"),
        timeout=float(os.getenv("DISCORD_BOT_TIMEOUT_SECONDS", "10")),
    )

    try:
        yield
    finally:
        if getattr(app.state, "rabbitmq_connection", None) is not None:
            await app.state.rabbitmq_connection.close()
        redis_client = getattr(app.state, "redis", None)
        if redis_client is not None:
            await redis_client.aclose()
        discord_bot_client = getattr(app.state, "discord_bot_client", None)
        if discord_bot_client is not None:
            await discord_bot_client.aclose()


app = FastAPI(lifespan=lifespan)

_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.post(
    "/v1/projects/{project_id}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
)
async def create_api_key(
    project_id: str,
    payload: CreateApiKeyRequest,
    authorization: str | None = Header(default=None),
):
    user_id = _resolve_authenticated_user_id(authorization)

    project_response = (
        supabase.table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("owner_id", user_id)
        .limit(1)
        .execute()
    )
    if not project_response.data:
        raise HTTPException(status_code=404, detail="Project not found")

    raw_key = _generate_api_key()
    key_hash = _hash_api_key(raw_key)

    insert_response = (
        supabase.table("api_keys")
        .insert(
            {
                "project_id": project_id,
                "key_hash": key_hash,
                "label": payload.label,
            }
        )
        .select("id, project_id, label, created_at")
        .execute()
    )
    rows = cast(list[dict[str, Any]], insert_response.data or [])
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to create API key")
    row = rows[0]

    return ApiKeyCreatedResponse(
        id=row["id"],
        project_id=row["project_id"],
        label=row["label"],
        created_at=row["created_at"],
        raw_key=raw_key,
    )


@app.get("/v1/projects/{project_id}/bot-status", response_model=BotStatusResponse)
async def get_bot_status(
    project_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
):
    user_id = _resolve_authenticated_user_id(authorization)

    project_response = (
        supabase.table("projects")
        .select("id, guild_id")
        .eq("id", project_id)
        .eq("owner_id", user_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], project_response.data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")

    guild_id = rows[0].get("guild_id")
    if not guild_id:
        return BotStatusResponse(project_id=project_id, guild_id=None, installed=False)

    client = getattr(request.app.state, "discord_bot_client", None)
    if client is None:
        raise HTTPException(
            status_code=503, detail="discord-bot client not initialized"
        )

    try:
        resp = await client.get(f"/v1/guilds/{guild_id}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="discord-bot unreachable") from exc
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="discord-bot returned an error")

    installed = bool(resp.json().get("installed", False))
    return BotStatusResponse(
        project_id=project_id, guild_id=guild_id, installed=installed
    )


@app.get("/v1/events/{event_id}")
async def get_event_status(event_id: str, request: Request):
    store: EventStatusStore = request.app.state.event_status_store
    status = await store.get(event_id)
    if status is None:
        raise HTTPException(status_code=404, detail="event_id not found")
    return {"event_id": event_id, "status": status}


@app.post("/v1/events", status_code=status.HTTP_202_ACCEPTED)
async def publish_event(
    payload: PublishEventRequest,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
):
    rabbitmq_exchange = getattr(request.app.state, "rabbitmq_exchange", None)
    rabbitmq_channel = getattr(request.app.state, "rabbitmq_channel", None)
    if rabbitmq_exchange is None or rabbitmq_channel is None:
        raise HTTPException(status_code=503, detail="RabbitMQ not initialized")

    api_key = _extract_api_key(x_api_key, authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    guild_id = await _resolve_guild_id_from_api_key(api_key)
    if guild_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    rate_limit_store: RateLimitStore = request.app.state.rate_limit_store
    window_seconds: int = request.app.state.rate_limit_window_seconds
    max_requests: int = request.app.state.rate_limit_max_requests
    count = await rate_limit_store.increment(_hash_api_key(api_key), window_seconds)
    if count > max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window_seconds)},
        )

    event_id = str(uuid.uuid4())
    store: EventStatusStore = request.app.state.event_status_store
    await store.set(event_id, EventStatus.pending)

    event = EventPayload(
        guild_id=guild_id,
        event_type=payload.event_type,
        data=payload.data,
    )
    body = event.model_dump_json().encode("utf-8")

    routing_key = getattr(request.app.state, "rabbitmq_routing_key", None)
    if not routing_key:
        raise HTTPException(
            status_code=503, detail="RabbitMQ routing key not configured"
        )
    message = aio_pika.Message(
        body=body,
        headers={"event_id": event_id},
        content_type="application/json",
    )
    try:
        await rabbitmq_exchange.publish(message, routing_key=routing_key)
    except Exception as exc:
        await store.set(event_id, EventStatus.failed_processing)
        raise HTTPException(status_code=503, detail="Failed to enqueue event") from exc

    return {"event_id": event_id}
