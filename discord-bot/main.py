import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from models import GuildStatusResponse, MessageRequest

DISCORD_API_BASE = os.getenv("DISCORD_API_BASE", "https://discord.com/api/v10")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/v1/guilds/{guild_id}", response_model=GuildStatusResponse)
async def get_guild_status(guild_id: str, request: Request) -> GuildStatusResponse:
    if not DISCORD_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="DISCORD_BOT_TOKEN is not set")

    url = f"{DISCORD_API_BASE}/guilds/{guild_id}"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    client: httpx.AsyncClient = request.app.state.http_client
    resp = await client.get(url, headers=headers)

    if resp.status_code == 200:
        return GuildStatusResponse(guild_id=guild_id, installed=True)
    # 403 (Missing Access) means the bot is not in the guild; 404 means the
    # guild id does not exist — both read as "not installed" to the caller.
    if resp.status_code in (403, 404):
        return GuildStatusResponse(guild_id=guild_id, installed=False)
    raise HTTPException(status_code=502, detail=resp.text)


@app.post("/v1/messages")
async def send_message(payload: MessageRequest, request: Request) -> dict[str, Any]:
    if not DISCORD_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="DISCORD_BOT_TOKEN is not set")

    url = f"{DISCORD_API_BASE}/channels/{payload.channel_id}/messages"
    body: dict[str, Any] = {}
    if payload.content:
        body["content"] = payload.content
    if payload.embeds:
        body["embeds"] = [
            embed.model_dump(exclude_none=True) for embed in payload.embeds
        ]

    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    client: httpx.AsyncClient = request.app.state.http_client
    resp = await client.post(url, json=body, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
