from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PublishEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    event_type: str = Field(validation_alias=AliasChoices("event_type", "eventType"))
    data: dict


class CreateApiKeyRequest(BaseModel):
    label: str | None = None


class BotStatusResponse(BaseModel):
    project_id: str
    guild_id: str | None
    installed: bool


class ApiKeyCreatedResponse(BaseModel):
    id: str
    project_id: str
    label: str | None
    created_at: str
    raw_key: str
