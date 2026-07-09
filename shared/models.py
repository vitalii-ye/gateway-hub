from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventStatus(StrEnum):
    pending = "PENDING"
    processed = "PROCESSED"
    failed_rate_limited = "FAILED_RATE_LIMITED"
    failed_invalid_payload = "FAILED_INVALID_PAYLOAD"
    failed_processing = "FAILED_PROCESSING"
    failed_downstream = "FAILED_DOWNSTREAM"
    ignored_no_config = "IGNORED_NO_CONFIG"
    ignored_no_match = "IGNORED_NO_MATCH"


class EventPayload(BaseModel):
    guild_id: str
    event_type: str
    data: dict[str, Any]


class RuleAction(BaseModel):
    type: str
    channel_id: str | None = None
    content: str | None = None


class Rule(BaseModel):
    event_type: str
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: list[RuleAction] = Field(default_factory=list)


class GuildConfig(BaseModel):
    rules: list[Rule] = Field(default_factory=list)
