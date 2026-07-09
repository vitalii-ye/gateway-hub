"""API tests for POST /v1/messages, with Discord mocked via MockTransport."""

import main
import pytest
from conftest import BOT_TOKEN


class TestSendMessageHappyPath:
    def test_forwards_content_to_discord_channel_endpoint(self, client, discord_api):
        response = client.post(
            "/v1/messages",
            json={"channel_id": "ch-123", "content": "hello"},
        )

        assert response.status_code == 200
        assert response.json() == {"id": "message-1"}
        assert len(discord_api.requests) == 1
        request = discord_api.last_request
        assert str(request.url) == (f"{main.DISCORD_API_BASE}/channels/ch-123/messages")
        assert discord_api.last_body == {"content": "hello"}

    def test_sends_bot_authorization_header(self, client, discord_api):
        client.post("/v1/messages", json={"channel_id": "ch-123", "content": "hi"})

        assert discord_api.last_request.headers["Authorization"] == f"Bot {BOT_TOKEN}"

    def test_forwards_embeds_excluding_unset_fields(self, client, discord_api):
        response = client.post(
            "/v1/messages",
            json={
                "channel_id": "ch-123",
                "embeds": [
                    {
                        "title": "Purchase",
                        "fields": [{"name": "item", "value": "sword"}],
                    }
                ],
            },
        )

        assert response.status_code == 200
        assert discord_api.last_body == {
            "embeds": [
                {
                    "title": "Purchase",
                    "fields": [{"name": "item", "value": "sword"}],
                }
            ]
        }

    def test_forwards_content_and_embeds_together(self, client, discord_api):
        client.post(
            "/v1/messages",
            json={
                "channel_id": "ch-123",
                "content": "hello",
                "embeds": [{"description": "details", "color": 65280}],
            },
        )

        assert discord_api.last_body == {
            "content": "hello",
            "embeds": [{"description": "details", "color": 65280}],
        }


class TestSendMessageErrors:
    def test_missing_bot_token_returns_500(
        self, client, discord_api, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(main, "DISCORD_BOT_TOKEN", None)

        response = client.post(
            "/v1/messages",
            json={"channel_id": "ch-123", "content": "hello"},
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "DISCORD_BOT_TOKEN is not set"
        assert discord_api.requests == []

    def test_discord_4xx_is_propagated_with_body_as_detail(self, client, discord_api):
        discord_api.response_status = 403
        discord_api.response_text = '{"message": "Missing Access", "code": 50001}'

        response = client.post(
            "/v1/messages",
            json={"channel_id": "ch-123", "content": "hello"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == discord_api.response_text

    def test_discord_5xx_is_propagated(self, client, discord_api):
        discord_api.response_status = 502
        discord_api.response_text = "Bad Gateway"

        response = client.post(
            "/v1/messages",
            json={"channel_id": "ch-123", "content": "hello"},
        )

        assert response.status_code == 502


class TestRequestValidation:
    def test_missing_channel_id_returns_422(self, client, discord_api):
        response = client.post("/v1/messages", json={"content": "hello"})

        assert response.status_code == 422
        assert discord_api.requests == []

    def test_empty_channel_id_returns_422(self, client):
        response = client.post(
            "/v1/messages", json={"channel_id": "", "content": "hello"}
        )

        assert response.status_code == 422

    def test_neither_content_nor_embeds_returns_422(self, client, discord_api):
        response = client.post("/v1/messages", json={"channel_id": "ch-123"})

        assert response.status_code == 422
        assert discord_api.requests == []
