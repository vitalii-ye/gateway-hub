"""Tests for the Stores guild-config cache TTL.

Cached guild rules must expire (REDIS_GUILD_RULES_TTL_SECONDS) so rule
changes made in the dashboard propagate without a worker restart.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from main import Stores

from shared.models import GuildConfig


class FakeRedis:
    """Records set() calls; get() always misses."""

    def __init__(self) -> None:
        self.set_calls: list[tuple[str, str, dict[str, Any]]] = []

    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: str, **kwargs: Any) -> None:
        self.set_calls.append((key, value, kwargs))


def make_cfg(ttl: int | None) -> SimpleNamespace:
    return SimpleNamespace(
        event_status_prefix="event_status",
        guild_rules_prefix="guild_rules",
        audit_logs_prefix="audit_logs",
        guild_rules_ttl_seconds=ttl,
    )


@pytest.mark.parametrize("ttl", [60, None])
async def test_cache_miss_writes_guild_cfg_with_configured_ttl(
    monkeypatch: pytest.MonkeyPatch, ttl: int | None
):
    fake_redis = FakeRedis()
    stores = Stores(fake_redis, supabase=None, cfg=make_cfg(ttl))

    async def fake_fetch(guild_id: str) -> GuildConfig:
        return GuildConfig(rules=[])

    monkeypatch.setattr(stores, "_fetch_guild_cfg_from_supabase", fake_fetch)

    result = await stores.get_guild_cfg("guild-1")

    assert result == GuildConfig(rules=[])
    assert fake_redis.set_calls == [
        ("guild_rules:guild-1", GuildConfig(rules=[]).model_dump_json(), {"ex": ttl})
    ]
