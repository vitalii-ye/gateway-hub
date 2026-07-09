"""Unit tests for the Redis-backed stores, using fakeredis."""

import fakeredis.aioredis
import pytest
from main import EventStatusStore, RateLimitStore

from shared.models import EventStatus


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


class TestEventStatusStore:
    async def test_set_then_get_roundtrips_status(self, fake_redis):
        store = EventStatusStore(fake_redis, "event_status", ttl_seconds=None)

        await store.set("evt-1", EventStatus.pending)

        assert await store.get("evt-1") == EventStatus.pending

    async def test_get_unknown_event_returns_none(self, fake_redis):
        store = EventStatusStore(fake_redis, "event_status", ttl_seconds=None)

        assert await store.get("missing") is None

    async def test_get_returns_none_for_unparseable_value(self, fake_redis):
        store = EventStatusStore(fake_redis, "event_status", ttl_seconds=None)
        await fake_redis.set("event_status:evt-1", "NOT_A_STATUS")

        assert await store.get("evt-1") is None

    async def test_set_applies_ttl_when_configured(self, fake_redis):
        store = EventStatusStore(fake_redis, "event_status", ttl_seconds=120)

        await store.set("evt-1", EventStatus.processed)

        ttl = await fake_redis.ttl("event_status:evt-1")
        assert 0 < ttl <= 120

    async def test_set_without_ttl_persists_key(self, fake_redis):
        store = EventStatusStore(fake_redis, "event_status", ttl_seconds=None)

        await store.set("evt-1", EventStatus.processed)

        assert await fake_redis.ttl("event_status:evt-1") == -1

    async def test_keys_are_namespaced_by_prefix(self, fake_redis):
        store_a = EventStatusStore(fake_redis, "prefix_a", ttl_seconds=None)
        store_b = EventStatusStore(fake_redis, "prefix_b", ttl_seconds=None)

        await store_a.set("evt-1", EventStatus.pending)

        assert await store_b.get("evt-1") is None


class TestRateLimitStore:
    async def test_increment_counts_up_per_identifier(self, fake_redis):
        store = RateLimitStore(fake_redis, "rate_limit")

        counts = [await store.increment("key-hash", 60) for _ in range(3)]

        assert counts == [1, 2, 3]

    async def test_identifiers_are_counted_independently(self, fake_redis):
        store = RateLimitStore(fake_redis, "rate_limit")

        await store.increment("first", 60)
        count = await store.increment("second", 60)

        assert count == 1

    async def test_increment_sets_expiry_on_window(self, fake_redis):
        store = RateLimitStore(fake_redis, "rate_limit")

        await store.increment("key-hash", 60)

        ttl = await fake_redis.ttl("rate_limit:key-hash")
        assert 0 < ttl <= 60

    async def test_get_returns_zero_for_unknown_identifier(self, fake_redis):
        store = RateLimitStore(fake_redis, "rate_limit")

        assert await store.get("unknown") == 0

    async def test_reset_clears_counter(self, fake_redis):
        store = RateLimitStore(fake_redis, "rate_limit")
        await store.increment("key-hash", 60)
        await store.increment("key-hash", 60)

        await store.reset("key-hash")

        assert await store.get("key-hash") == 0
