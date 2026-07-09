"""Shared fixtures for gateway tests.

The gateway's lifespan connects to real Redis and RabbitMQ, so tests
instantiate TestClient WITHOUT the context manager (lifespan never runs)
and populate ``app.state`` with fakes instead.

SUPABASE_URL / SUPABASE_KEY must exist before anything imports shared.db,
which creates a client at import time.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")

from types import SimpleNamespace  # noqa: E402
from typing import Any  # noqa: E402

import fakeredis.aioredis  # noqa: E402
import main  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

VALID_API_KEY = "gwh_valid-test-key"
GUILD_ID = "guild-123"
RATE_LIMIT_MAX_REQUESTS = 3
RATE_LIMIT_WINDOW_SECONDS = 60
VALID_USER_JWT = "valid-user-jwt"
USER_ID = "user-1"


class FakeQuery:
    """Chainable stand-in for a supabase table query."""

    def __init__(self, rows: list[dict[str, Any]], calls: list[tuple]) -> None:
        self._rows = rows
        self._calls = calls

    def select(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self

    def update(self, values: dict[str, Any]) -> "FakeQuery":
        self._calls.append(("update", values))
        return self

    def insert(self, values: dict[str, Any]) -> "FakeQuery":
        self._calls.append(("insert", values))
        return self

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self._rows = [row for row in self._rows if row.get(column) == value]
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._rows)


class FakeAuth:
    """Accepts VALID_USER_JWT and rejects everything else, like supabase.auth."""

    def get_user(self, jwt: str) -> SimpleNamespace:
        if jwt != VALID_USER_JWT:
            raise ValueError("invalid JWT")
        return SimpleNamespace(user=SimpleNamespace(id=USER_ID))


class FakeSupabase:
    """Minimal supabase client fake: table() returns a filterable query."""

    def __init__(self) -> None:
        self.rows_by_table: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[tuple] = []
        self.auth = FakeAuth()

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(list(self.rows_by_table.get(name, [])), self.calls)


class FakeExchange:
    """Records published messages; can be told to fail."""

    def __init__(self) -> None:
        self.published: list[tuple[Any, str]] = []
        self.fail = False

    async def publish(self, message: Any, routing_key: str) -> None:
        if self.fail:
            raise ConnectionError("broker unavailable")
        self.published.append((message, routing_key))


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def fake_exchange() -> FakeExchange:
    return FakeExchange()


@pytest.fixture
def fake_supabase(monkeypatch: pytest.MonkeyPatch) -> FakeSupabase:
    fake = FakeSupabase()
    fake.rows_by_table["api_keys"] = [
        {
            "id": "key-1",
            "key_hash": main._hash_api_key(VALID_API_KEY),
            "project_id": "proj-1",
            "projects": {"guild_id": GUILD_ID},
        }
    ]
    monkeypatch.setattr(main, "supabase", fake)
    return fake


@pytest.fixture
def event_status_store(fake_redis) -> main.EventStatusStore:
    return main.EventStatusStore(fake_redis, "event_status", ttl_seconds=3600)


@pytest.fixture
def client(
    fake_redis,
    fake_exchange: FakeExchange,
    fake_supabase: FakeSupabase,
    event_status_store: main.EventStatusStore,
) -> TestClient:
    app = main.app
    app.state.event_status_store = event_status_store
    app.state.rate_limit_store = main.RateLimitStore(fake_redis, "rate_limit")
    app.state.rate_limit_max_requests = RATE_LIMIT_MAX_REQUESTS
    app.state.rate_limit_window_seconds = RATE_LIMIT_WINDOW_SECONDS
    app.state.rabbitmq_channel = object()
    app.state.rabbitmq_exchange = fake_exchange
    app.state.rabbitmq_routing_key = "events"
    # No context manager: entering it would run the lifespan, which needs
    # real Redis/RabbitMQ.
    return TestClient(app)
