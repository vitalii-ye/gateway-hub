"""Tests for GET /v1/projects/{project_id}/bot-status."""

from typing import Any

import httpx
import main
import pytest
from conftest import GUILD_ID, USER_ID, VALID_USER_JWT, FakeSupabase
from fastapi.testclient import TestClient

PROJECT_ID = "proj-1"
AUTH_HEADERS = {"Authorization": f"Bearer {VALID_USER_JWT}"}


class DiscordBotRecorder:
    """MockTransport handler standing in for the discord-bot service."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.response_status = 200
        self.response_json: dict[str, Any] = {"guild_id": GUILD_ID, "installed": True}
        self.raise_connect_error = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.raise_connect_error:
            raise httpx.ConnectError("connection refused", request=request)
        self.requests.append(request)
        return httpx.Response(self.response_status, json=self.response_json)


@pytest.fixture
def discord_bot() -> DiscordBotRecorder:
    return DiscordBotRecorder()


@pytest.fixture
def bot_status_client(
    client: TestClient,
    fake_supabase: FakeSupabase,
    discord_bot: DiscordBotRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    fake_supabase.rows_by_table["projects"] = [
        {"id": PROJECT_ID, "owner_id": USER_ID, "guild_id": GUILD_ID}
    ]
    monkeypatch.setattr(
        main.app.state,
        "discord_bot_client",
        httpx.AsyncClient(
            transport=httpx.MockTransport(discord_bot),
            base_url="http://discord-bot:8001",
        ),
        raising=False,
    )
    return client


def test_missing_bearer_token_returns_401(bot_status_client: TestClient):
    response = bot_status_client.get(f"/v1/projects/{PROJECT_ID}/bot-status")

    assert response.status_code == 401


def test_invalid_bearer_token_returns_401(bot_status_client: TestClient):
    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status",
        headers={"Authorization": "Bearer garbage"},
    )

    assert response.status_code == 401


def test_unknown_project_returns_404(bot_status_client: TestClient):
    response = bot_status_client.get(
        "/v1/projects/no-such-project/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 404


def test_project_owned_by_someone_else_returns_404(
    bot_status_client: TestClient, fake_supabase: FakeSupabase
):
    fake_supabase.rows_by_table["projects"] = [
        {"id": PROJECT_ID, "owner_id": "someone-else", "guild_id": GUILD_ID}
    ]

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 404


@pytest.mark.parametrize("blank_guild", [None, ""])
def test_unconfigured_guild_short_circuits_to_not_installed(
    bot_status_client: TestClient,
    fake_supabase: FakeSupabase,
    discord_bot: DiscordBotRecorder,
    blank_guild: str | None,
):
    fake_supabase.rows_by_table["projects"] = [
        {"id": PROJECT_ID, "owner_id": USER_ID, "guild_id": blank_guild}
    ]

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": PROJECT_ID,
        "guild_id": None,
        "installed": False,
    }
    assert discord_bot.requests == []


@pytest.mark.parametrize("installed", [True, False])
def test_installed_state_passed_through_from_discord_bot(
    bot_status_client: TestClient, discord_bot: DiscordBotRecorder, installed: bool
):
    discord_bot.response_json = {"guild_id": GUILD_ID, "installed": installed}

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": PROJECT_ID,
        "guild_id": GUILD_ID,
        "installed": installed,
    }
    assert discord_bot.requests[-1].url.path == f"/v1/guilds/{GUILD_ID}"


def test_discord_bot_unreachable_returns_503(
    bot_status_client: TestClient, discord_bot: DiscordBotRecorder
):
    discord_bot.raise_connect_error = True

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "discord-bot unreachable"


def test_missing_discord_bot_client_returns_503(
    bot_status_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delattr(main.app.state, "discord_bot_client")

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 503


def test_discord_bot_error_returns_502(
    bot_status_client: TestClient, discord_bot: DiscordBotRecorder
):
    discord_bot.response_status = 500
    discord_bot.response_json = {"detail": "boom"}

    response = bot_status_client.get(
        f"/v1/projects/{PROJECT_ID}/bot-status", headers=AUTH_HEADERS
    )

    assert response.status_code == 502
