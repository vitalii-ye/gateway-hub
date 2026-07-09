import asyncio
import json
import logging
import os
import time
from typing import Any

import aio_pika
import httpx
import redis.asyncio as redis
from models import ProjectRow, RuleRow
from pydantic import ValidationError
from supabase import Client

from shared.config import RedisConfig, build_rabbitmq_url, load_redis_config
from shared.db import supabase
from shared.models import EventPayload, EventStatus, GuildConfig, Rule, RuleAction

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("rules-engine")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


def _json_loads_bytes(body: bytes) -> EventPayload:
    # Fast reject poison messages early.
    return EventPayload.model_validate_json(body)


def _get_by_path(obj: dict[str, Any], path: str) -> Any:
    # Supports paths like: "data.item".
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _rule_matches(event: EventPayload, rule: Rule) -> bool:
    if rule.event_type != event.event_type:
        return False
    for k, expected in rule.conditions.items():
        actual = _get_by_path(event.model_dump(), str(k))
        if actual != expected:
            return False
    return True


def evaluate_rules(event: EventPayload, guild_cfg: GuildConfig) -> list[RuleAction]:
    actions: list[RuleAction] = []
    for rule in guild_cfg.rules:
        if _rule_matches(event, rule):
            actions.extend(rule.actions)
    return actions


def _render_message_template(template: str, event: EventPayload) -> str:
    rendered = template
    replacements = {
        "{{guild_id}}": event.guild_id,
        "{{event_type}}": event.event_type,
        "{{item}}": str(event.data.get("item", "")),
        "{{user_id}}": str(event.data.get("user_id", "")),
        "{{username}}": str(event.data.get("username", "")),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


class Stores:
    def __init__(self, client: redis.Redis, supabase: Client, cfg: RedisConfig) -> None:
        self._client = client
        self._supabase = supabase
        self._cfg = cfg

    def event_status_key(self, event_id: str) -> str:
        return f"{self._cfg.event_status_prefix}:{event_id}"

    def guild_rules_key(self, guild_id: str) -> str:
        return f"{self._cfg.guild_rules_prefix}:{guild_id}"

    def audit_logs_key(self, guild_id: str) -> str:
        return f"{self._cfg.audit_logs_prefix}:{guild_id}"

    async def _fetch_guild_cfg_from_supabase(self, guild_id: str) -> GuildConfig | None:
        projects_response = (
            self._supabase.table("projects")
            .select("*")
            .eq("guild_id", guild_id)
            .execute()
        )
        projects = projects_response.data or []
        if not projects:
            return None

        project = ProjectRow.model_validate(projects[0])

        rules_response = (
            self._supabase.table("rules")
            .select("*")
            .eq("project_id", project.id)
            .eq("enabled", True)
            .execute()
        )
        rules = rules_response.data or []
        if not rules:
            return GuildConfig(rules=[])

        guild_rules: list[Rule] = []
        for row in rules:
            rule_row = RuleRow.model_validate(row)
            conditions = rule_row.conditions or {}
            guild_rules.append(
                Rule(
                    event_type=rule_row.event_type,
                    conditions=conditions,
                    actions=[
                        RuleAction(
                            type="SEND_MESSAGE",
                            channel_id=rule_row.discord_channel_id,
                            content=rule_row.message_template,
                        )
                    ],
                )
            )

        return GuildConfig(rules=guild_rules)

    async def warm_guild_cfg_cache(self) -> None:
        projects_response = self._supabase.table("projects").select("*").execute()
        projects = projects_response.data or []
        for project in projects:
            project_row = ProjectRow.model_validate(project)
            guild_cfg = await self._fetch_guild_cfg_from_supabase(project_row.guild_id)
            if guild_cfg is None:
                continue
            await self._client.set(
                self.guild_rules_key(project_row.guild_id),
                guild_cfg.model_dump_json(),
                ex=self._cfg.guild_rules_ttl_seconds,
            )
            logger.info("warmed guild config guild_id=%s", project_row.guild_id)

    async def get_guild_cfg(self, guild_id: str) -> GuildConfig | None:
        raw = await self._client.get(self.guild_rules_key(guild_id))
        if raw is not None:
            try:
                obj = json.loads(raw)
                return GuildConfig.model_validate(obj)
            except (json.JSONDecodeError, ValidationError):
                logger.warning("invalid cached guild config guild_id=%s", guild_id)

        guild_cfg = await self._fetch_guild_cfg_from_supabase(guild_id)
        if guild_cfg is None:
            return None

        await self._client.set(
            self.guild_rules_key(guild_id),
            guild_cfg.model_dump_json(),
            ex=self._cfg.guild_rules_ttl_seconds,
        )
        return guild_cfg

    async def set_event_status(self, event_id: str, status: EventStatus) -> None:
        await self._client.set(self.event_status_key(event_id), status.value)

    async def append_audit_log(self, guild_id: str, entry: dict[str, Any]) -> None:
        await self._client.rpush(self.audit_logs_key(guild_id), json.dumps(entry))


class DiscordBotClient:
    def __init__(self) -> None:
        base = os.getenv("DISCORD_BOT_URL", "http://discord-bot:9000")
        path = os.getenv("DISCORD_BOT_EXECUTE_PATH", "/v1/messages")
        self._url = base.rstrip("/") + path
        self._timeout = float(os.getenv("DISCORD_BOT_TIMEOUT_SECONDS", "10"))
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def execute(self, payload: dict[str, Any]) -> None:
        resp = await self._client.post(self._url, json=payload)
        # Treat non-2xx as failure (retryable unless you decide otherwise later).
        resp.raise_for_status()


async def handle_message(
    message: aio_pika.IncomingMessage,
    *,
    stores: Stores,
    discord: DiscordBotClient,
) -> None:
    event_id = None
    try:
        event_id = (message.headers or {}).get("event_id")
        if not event_id or not isinstance(event_id, str):
            # Poison message, drop it.
            await message.reject(requeue=False)
            return

        # Parse payload (poison messages are ACKed as failed to avoid infinite retries).
        try:
            event = _json_loads_bytes(message.body)
        except ValidationError as exc:
            await stores.set_event_status(event_id, EventStatus.failed_invalid_payload)
            logger.warning("invalid payload event_id=%s err=%s", event_id, exc)
            await message.ack()
            return

        guild_id = event.guild_id

        guild_cfg = await stores.get_guild_cfg(guild_id)
        if guild_cfg is None:
            await stores.set_event_status(event_id, EventStatus.ignored_no_config)
            await message.ack()
            return

        actions = evaluate_rules(event, guild_cfg)
        if not actions:
            await stores.set_event_status(event_id, EventStatus.ignored_no_match)
            await stores.append_audit_log(
                guild_id,
                {
                    "ts": int(time.time()),
                    "event_id": event_id,
                    "guild_id": guild_id,
                    "outcome": EventStatus.ignored_no_match.value,
                    "event": event.model_dump(),
                },
            )
            await message.ack()
            return

        message_payloads: list[dict[str, Any]] = []
        for action in actions:
            if action.type != "SEND_MESSAGE":
                continue
            channel_id = action.channel_id
            content = action.content
            if not channel_id or not content:
                continue
            message_payloads.append(
                {
                    "channel_id": channel_id,
                    "content": _render_message_template(content, event),
                }
            )

        if not message_payloads:
            await stores.set_event_status(event_id, EventStatus.failed_processing)
            await stores.append_audit_log(
                guild_id,
                {
                    "ts": int(time.time()),
                    "event_id": event_id,
                    "guild_id": guild_id,
                    "outcome": EventStatus.failed_processing.value,
                    "actions": [a.model_dump() for a in actions],
                },
            )
            await message.ack()
            return

        for payload in message_payloads:
            await discord.execute(payload)

        await stores.set_event_status(event_id, EventStatus.processed)
        await stores.append_audit_log(
            guild_id,
            {
                "ts": int(time.time()),
                "event_id": event_id,
                "guild_id": guild_id,
                "outcome": EventStatus.processed.value,
                "actions": [a.model_dump() for a in actions],
            },
        )
        await message.ack()
    except httpx.HTTPError as exc:
        # Downstream or network issue; keep message in queue for retries.
        if event_id:
            await stores.set_event_status(event_id, EventStatus.failed_downstream)
        logger.warning("downstream failed event_id=%s err=%s", event_id, exc)
        await message.nack(requeue=True)
    except Exception as exc:
        if event_id:
            await stores.set_event_status(event_id, EventStatus.failed_processing)
        logger.exception("processing failed event_id=%s err=%s", event_id, exc)
        await message.nack(requeue=True)


async def run() -> None:
    redis_cfg = load_redis_config()
    redis_client = redis.from_url(redis_cfg.url, decode_responses=True)
    if not redis_cfg.guild_rules_prefix or not redis_cfg.audit_logs_prefix:
        raise RuntimeError(
            "REDIS_GUILD_RULES_PREFIX and REDIS_AUDIT_LOGS_PREFIX are required"
        )
    stores = Stores(redis_client, supabase, redis_cfg)

    rabbitmq_url = build_rabbitmq_url()
    queue_name = os.getenv("RABBITMQ_QUEUE", "events")

    discord = DiscordBotClient()
    connection: aio_pika.RobustConnection | None = None
    try:
        connection = await aio_pika.connect_robust(rabbitmq_url)
        channel = await connection.channel()
        prefetch = int(os.getenv("WORKER_PREFETCH", "10"))
        await channel.set_qos(prefetch_count=prefetch)

        try:
            await stores.warm_guild_cfg_cache()
        except Exception as exc:
            logger.warning("failed to warm guild config cache err=%s", exc)

        queue = await channel.declare_queue(queue_name, durable=True)
        logger.info("worker started queue=%s prefetch=%s", queue_name, prefetch)

        async def _consumer(msg: aio_pika.IncomingMessage) -> None:
            # Do not auto-ack: we decide ACK/NACK based on execution outcome.
            await handle_message(msg, stores=stores, discord=discord)

        await queue.consume(_consumer, no_ack=False)
        await asyncio.Future()
    finally:
        await discord.aclose()
        await redis_client.aclose()
        if connection is not None:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
