import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RedisConfig:
    url: str
    event_status_prefix: str
    rate_limit_prefix: str | None
    guild_rules_prefix: str | None
    audit_logs_prefix: str | None
    event_status_ttl_seconds: int | None
    guild_rules_ttl_seconds: int | None


def load_redis_config() -> RedisConfig:
    ttl_raw = os.getenv("REDIS_EVENT_STATUS_TTL_SECONDS")
    ttl = int(ttl_raw) if ttl_raw else None
    # Cached guild rules expire so dashboard rule changes propagate without a
    # worker restart; set to empty to cache forever.
    guild_rules_ttl_raw = os.getenv("REDIS_GUILD_RULES_TTL_SECONDS", "60")
    guild_rules_ttl = int(guild_rules_ttl_raw) if guild_rules_ttl_raw else None
    return RedisConfig(
        url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        event_status_prefix=os.getenv("REDIS_EVENT_STATUS_PREFIX", "event_status"),
        rate_limit_prefix=os.getenv("REDIS_RATE_LIMIT_PREFIX", "rate_limit"),
        guild_rules_prefix=os.getenv("REDIS_GUILD_RULES_PREFIX", "guild_rules"),
        audit_logs_prefix=os.getenv("REDIS_AUDIT_LOGS_PREFIX", "audit_logs"),
        event_status_ttl_seconds=ttl,
        guild_rules_ttl_seconds=guild_rules_ttl,
    )


def build_rabbitmq_url() -> str:
    explicit_url = os.getenv("RABBITMQ_URL")
    if explicit_url:
        return explicit_url
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = os.getenv("RABBITMQ_PORT", "5672")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    vhost = os.getenv("RABBITMQ_VHOST", "/")
    vhost = vhost.lstrip("/")
    vhost_path = f"/{vhost}" if vhost else "/"
    return f"amqp://{user}:{password}@{host}:{port}{vhost_path}"
