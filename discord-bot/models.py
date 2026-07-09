from pydantic import BaseModel, Field, model_validator


class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool | None = None


class Embed(BaseModel):
    title: str | None = None
    description: str | None = None
    color: int | None = None
    fields: list[EmbedField] | None = None


class GuildStatusResponse(BaseModel):
    guild_id: str
    installed: bool


class MessageRequest(BaseModel):
    channel_id: str = Field(..., min_length=1)
    content: str | None = None
    embeds: list[Embed] | None = None

    @model_validator(mode="after")
    def validate_body(self):
        if not self.content and not self.embeds:
            raise ValueError("content or embeds must be provided")
        return self
