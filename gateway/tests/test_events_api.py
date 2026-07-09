"""API tests for the gateway event endpoints, run against fakes.

TestClient is used without the lifespan; app.state is populated in conftest.
"""

import json

from conftest import GUILD_ID, RATE_LIMIT_MAX_REQUESTS, VALID_API_KEY


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPublishEvent:
    def test_happy_path_accepts_event_and_publishes_message(
        self, client, fake_exchange
    ):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": VALID_API_KEY},
            json={"event_type": "item_purchased", "data": {"item": "sword"}},
        )

        assert response.status_code == 202
        event_id = response.json()["event_id"]
        assert event_id

        assert len(fake_exchange.published) == 1
        message, routing_key = fake_exchange.published[0]
        assert routing_key == "events"
        assert message.headers == {"event_id": event_id}
        body = json.loads(message.body)
        assert body == {
            "guild_id": GUILD_ID,
            "event_type": "item_purchased",
            "data": {"item": "sword"},
        }

    def test_happy_path_marks_event_pending(self, client):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": VALID_API_KEY},
            json={"event_type": "item_purchased", "data": {}},
        )
        event_id = response.json()["event_id"]

        status_response = client.get(f"/v1/events/{event_id}")

        assert status_response.status_code == 200
        assert status_response.json() == {"event_id": event_id, "status": "PENDING"}

    def test_accepts_key_via_bearer_authorization(self, client, fake_exchange):
        response = client.post(
            "/v1/events",
            headers={"Authorization": f"Bearer {VALID_API_KEY}"},
            json={"event_type": "item_purchased", "data": {}},
        )

        assert response.status_code == 202
        assert len(fake_exchange.published) == 1

    def test_accepts_camel_case_event_type_alias(self, client, fake_exchange):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": VALID_API_KEY},
            json={"eventType": "item_purchased", "data": {}},
        )

        assert response.status_code == 202
        message, _ = fake_exchange.published[0]
        assert json.loads(message.body)["event_type"] == "item_purchased"

    def test_missing_api_key_returns_401(self, client, fake_exchange):
        response = client.post(
            "/v1/events",
            json={"event_type": "item_purchased", "data": {}},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"
        assert fake_exchange.published == []

    def test_invalid_api_key_returns_401(self, client, fake_exchange):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": "gwh_wrong-key"},
            json={"event_type": "item_purchased", "data": {}},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"
        assert fake_exchange.published == []

    def test_request_missing_event_type_returns_422(self, client):
        response = client.post(
            "/v1/events",
            headers={"X-API-Key": VALID_API_KEY},
            json={"data": {}},
        )

        assert response.status_code == 422

    def test_rate_limit_exceeded_returns_429_with_retry_after(
        self, client, fake_exchange
    ):
        payload = {"event_type": "item_purchased", "data": {}}
        headers = {"X-API-Key": VALID_API_KEY}
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            assert (
                client.post("/v1/events", headers=headers, json=payload).status_code
                == 202
            )

        response = client.post("/v1/events", headers=headers, json=payload)

        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded"
        assert response.headers["Retry-After"] == "60"
        assert len(fake_exchange.published) == RATE_LIMIT_MAX_REQUESTS

    def test_publish_failure_returns_503_and_marks_event_failed(
        self, client, fake_exchange
    ):
        fake_exchange.fail = True

        response = client.post(
            "/v1/events",
            headers={"X-API-Key": VALID_API_KEY},
            json={"event_type": "item_purchased", "data": {}},
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "Failed to enqueue event"


class TestGetEventStatus:
    def test_unknown_event_returns_404(self, client):
        response = client.get("/v1/events/does-not-exist")

        assert response.status_code == 404
        assert response.json()["detail"] == "event_id not found"
