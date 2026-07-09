"""Tests for shared.config: RabbitMQ URL composition and Redis config parsing."""

import pytest

from shared.config import build_rabbitmq_url, load_redis_config

RABBITMQ_ENV_VARS = [
    "RABBITMQ_URL",
    "RABBITMQ_HOST",
    "RABBITMQ_PORT",
    "RABBITMQ_USER",
    "RABBITMQ_PASSWORD",
    "RABBITMQ_VHOST",
]

REDIS_ENV_VARS = [
    "REDIS_URL",
    "REDIS_EVENT_STATUS_PREFIX",
    "REDIS_RATE_LIMIT_PREFIX",
    "REDIS_GUILD_RULES_PREFIX",
    "REDIS_AUDIT_LOGS_PREFIX",
    "REDIS_EVENT_STATUS_TTL_SECONDS",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for name in RABBITMQ_ENV_VARS + REDIS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


class TestBuildRabbitmqUrl:
    def test_defaults_compose_guest_localhost_url(self):
        assert build_rabbitmq_url() == "amqp://guest:guest@localhost:5672/"

    def test_explicit_url_wins_over_components(self, monkeypatch):
        monkeypatch.setenv("RABBITMQ_URL", "amqp://explicit:secret@broker:5673/vhost")
        monkeypatch.setenv("RABBITMQ_HOST", "ignored-host")
        monkeypatch.setenv("RABBITMQ_USER", "ignored-user")

        assert build_rabbitmq_url() == "amqp://explicit:secret@broker:5673/vhost"

    def test_composes_from_host_port_user_password(self, monkeypatch):
        monkeypatch.setenv("RABBITMQ_HOST", "rabbit.internal")
        monkeypatch.setenv("RABBITMQ_PORT", "5673")
        monkeypatch.setenv("RABBITMQ_USER", "svc")
        monkeypatch.setenv("RABBITMQ_PASSWORD", "s3cret")

        assert build_rabbitmq_url() == "amqp://svc:s3cret@rabbit.internal:5673/"

    def test_default_vhost_slash_renders_as_bare_slash(self, monkeypatch):
        monkeypatch.setenv("RABBITMQ_VHOST", "/")

        assert build_rabbitmq_url() == "amqp://guest:guest@localhost:5672/"

    def test_named_vhost_is_appended_as_path(self, monkeypatch):
        monkeypatch.setenv("RABBITMQ_VHOST", "events")

        assert build_rabbitmq_url() == "amqp://guest:guest@localhost:5672/events"

    def test_named_vhost_with_leading_slash_is_normalized(self, monkeypatch):
        monkeypatch.setenv("RABBITMQ_VHOST", "/events")

        assert build_rabbitmq_url() == "amqp://guest:guest@localhost:5672/events"


class TestLoadRedisConfig:
    def test_defaults(self):
        config = load_redis_config()

        assert config.url == "redis://localhost:6379/0"
        assert config.event_status_prefix == "event_status"
        assert config.rate_limit_prefix == "rate_limit"
        assert config.guild_rules_prefix == "guild_rules"
        assert config.audit_logs_prefix == "audit_logs"
        assert config.event_status_ttl_seconds is None
        assert config.guild_rules_ttl_seconds == 60

    def test_ttl_is_parsed_as_int(self, monkeypatch):
        monkeypatch.setenv("REDIS_EVENT_STATUS_TTL_SECONDS", "86400")

        assert load_redis_config().event_status_ttl_seconds == 86400

    def test_empty_ttl_is_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv("REDIS_EVENT_STATUS_TTL_SECONDS", "")

        assert load_redis_config().event_status_ttl_seconds is None

    def test_guild_rules_ttl_is_parsed_as_int(self, monkeypatch):
        monkeypatch.setenv("REDIS_GUILD_RULES_TTL_SECONDS", "300")

        assert load_redis_config().guild_rules_ttl_seconds == 300

    def test_empty_guild_rules_ttl_disables_expiry(self, monkeypatch):
        monkeypatch.setenv("REDIS_GUILD_RULES_TTL_SECONDS", "")

        assert load_redis_config().guild_rules_ttl_seconds is None

    def test_non_numeric_ttl_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("REDIS_EVENT_STATUS_TTL_SECONDS", "one-day")

        with pytest.raises(ValueError):
            load_redis_config()

    def test_env_overrides_url_and_prefixes(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://cache.internal:6380/1")
        monkeypatch.setenv("REDIS_EVENT_STATUS_PREFIX", "es")
        monkeypatch.setenv("REDIS_RATE_LIMIT_PREFIX", "rl")

        config = load_redis_config()

        assert config.url == "redis://cache.internal:6380/1"
        assert config.event_status_prefix == "es"
        assert config.rate_limit_prefix == "rl"
