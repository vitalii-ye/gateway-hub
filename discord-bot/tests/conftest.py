"""Shared fixtures for discord-bot tests.

TestClient is used without the context manager so the lifespan never runs;
app.state.http_client is replaced with an httpx client whose MockTransport
records outgoing Discord requests.
"""

import json
from typing import Any

import httpx
import main
import pytest
from fastapi.testclient import TestClient

BOT_TOKEN = "test-bot-token"


class DiscordAPIRecorder:
    """MockTransport handler recording requests and serving a canned response."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.response_status = 200
        self.response_json: dict[str, Any] = {"id": "message-1"}
        self.response_text: str | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.response_text is not None:
            return httpx.Response(self.response_status, text=self.response_text)
        return httpx.Response(self.response_status, json=self.response_json)

    @property
    def last_request(self) -> httpx.Request:
        return self.requests[-1]

    @property
    def last_body(self) -> dict[str, Any]:
        return json.loads(self.last_request.content)


@pytest.fixture
def discord_api() -> DiscordAPIRecorder:
    return DiscordAPIRecorder()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch, discord_api: DiscordAPIRecorder
) -> TestClient:
    monkeypatch.setattr(main, "DISCORD_BOT_TOKEN", BOT_TOKEN)
    main.app.state.http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(discord_api)
    )
    # No context manager: entering it would run the lifespan and replace the
    # mocked client with a real one.
    return TestClient(main.app)
