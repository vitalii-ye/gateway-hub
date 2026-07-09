"""Shared fixtures and fakes for rules-engine tests.

SUPABASE_URL / SUPABASE_KEY must exist before anything imports shared.db,
which creates a client at import time. handle_message is exercised with
duck-typed fakes for the aio-pika message, Stores, and DiscordBotClient.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")

from typing import Any  # noqa: E402

import pytest  # noqa: E402

from shared.models import EventPayload, GuildConfig  # noqa: E402


class FakeIncomingMessage:
    """Records ack/nack/reject decisions like an aio-pika IncomingMessage."""

    def __init__(self, body: bytes = b"", headers: dict[str, Any] | None = None):
        self.body = body
        self.headers = headers if headers is not None else {}
        self.acked = False
        self.nacked_requeue: bool | None = None
        self.rejected_requeue: bool | None = None

    async def ack(self) -> None:
        self.acked = True

    async def nack(self, requeue: bool = True) -> None:
        self.nacked_requeue = requeue

    async def reject(self, requeue: bool = False) -> None:
        self.rejected_requeue = requeue


class FakeStores:
    """In-memory stand-in for Stores."""

    def __init__(self, guild_configs: dict[str, GuildConfig] | None = None):
        self.guild_configs = guild_configs or {}
        self.statuses: dict[str, Any] = {}
        self.audit_logs: dict[str, list[dict[str, Any]]] = {}

    async def get_guild_cfg(self, guild_id: str) -> GuildConfig | None:
        return self.guild_configs.get(guild_id)

    async def set_event_status(self, event_id: str, status: Any) -> None:
        self.statuses[event_id] = status

    async def append_audit_log(self, guild_id: str, entry: dict[str, Any]) -> None:
        self.audit_logs.setdefault(guild_id, []).append(entry)


class FakeDiscordBotClient:
    """Records executed payloads; raises `error` first if configured."""

    def __init__(self, error: Exception | None = None):
        self.executed: list[dict[str, Any]] = []
        self.error = error

    async def execute(self, payload: dict[str, Any]) -> None:
        if self.error is not None:
            raise self.error
        self.executed.append(payload)


def make_event(
    guild_id: str = "guild-123",
    event_type: str = "item_purchased",
    data: dict[str, Any] | None = None,
) -> EventPayload:
    if data is None:
        data = {"item": "sword", "user_id": "42", "username": "alice"}
    return EventPayload(guild_id=guild_id, event_type=event_type, data=data)


def make_message(
    event: EventPayload | None = None,
    event_id: Any = "evt-1",
    body: bytes | None = None,
) -> FakeIncomingMessage:
    if body is None:
        body = (event or make_event()).model_dump_json().encode("utf-8")
    headers = {} if event_id is None else {"event_id": event_id}
    return FakeIncomingMessage(body=body, headers=headers)


@pytest.fixture
def discord() -> FakeDiscordBotClient:
    return FakeDiscordBotClient()
