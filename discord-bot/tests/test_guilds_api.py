"""Tests for GET /v1/guilds/{guild_id} (bot installed-status check)."""

import main
import pytest
from conftest import BOT_TOKEN, DiscordAPIRecorder
from fastapi.testclient import TestClient

GUILD_ID = "123456789012345678"


def test_installed_when_discord_returns_guild(
    client: TestClient, discord_api: DiscordAPIRecorder
):
    discord_api.response_json = {"id": GUILD_ID, "name": "Test Guild"}

    response = client.get(f"/v1/guilds/{GUILD_ID}")

    assert response.status_code == 200
    assert response.json() == {"guild_id": GUILD_ID, "installed": True}
    assert (
        str(discord_api.last_request.url)
        == f"{main.DISCORD_API_BASE}/guilds/{GUILD_ID}"
    )
    assert discord_api.last_request.headers["Authorization"] == f"Bot {BOT_TOKEN}"


@pytest.mark.parametrize("upstream_status", [403, 404])
def test_not_installed_when_bot_lacks_access(
    client: TestClient, discord_api: DiscordAPIRecorder, upstream_status: int
):
    discord_api.response_status = upstream_status
    discord_api.response_json = {"message": "Missing Access", "code": 50001}

    response = client.get(f"/v1/guilds/{GUILD_ID}")

    assert response.status_code == 200
    assert response.json() == {"guild_id": GUILD_ID, "installed": False}


def test_missing_token_returns_500_without_calling_discord(
    client: TestClient,
    discord_api: DiscordAPIRecorder,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(main, "DISCORD_BOT_TOKEN", None)

    response = client.get(f"/v1/guilds/{GUILD_ID}")

    assert response.status_code == 500
    assert response.json()["detail"] == "DISCORD_BOT_TOKEN is not set"
    assert discord_api.requests == []


def test_unexpected_discord_error_returns_502(
    client: TestClient, discord_api: DiscordAPIRecorder
):
    discord_api.response_status = 500
    discord_api.response_text = "Internal Server Error"

    response = client.get(f"/v1/guilds/{GUILD_ID}")

    assert response.status_code == 502
    assert "Internal Server Error" in response.json()["detail"]
