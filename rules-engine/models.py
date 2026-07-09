from typing import Any

from pydantic import BaseModel


class ProjectRow(BaseModel):
    id: str
    guild_id: str


class RuleRow(BaseModel):
    id: str | None = None
    project_id: str | None = None
    name: str | None = None
    event_type: str
    discord_channel_id: str
    message_template: str
    enabled: bool = True
    conditions: dict[str, Any] | None = None
