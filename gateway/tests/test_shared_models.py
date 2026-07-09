"""Validation tests for shared pydantic models."""

import pytest
from pydantic import ValidationError

from shared.models import EventPayload, EventStatus


class TestEventPayload:
    def test_valid_payload_parses(self):
        event = EventPayload(
            guild_id="guild-1",
            event_type="item_purchased",
            data={"item": "sword", "amount": 3},
        )

        assert event.guild_id == "guild-1"
        assert event.event_type == "item_purchased"
        assert event.data == {"item": "sword", "amount": 3}

    def test_json_roundtrip(self):
        event = EventPayload(guild_id="g", event_type="e", data={"k": "v"})

        parsed = EventPayload.model_validate_json(event.model_dump_json())

        assert parsed == event

    @pytest.mark.parametrize(
        "payload",
        [
            {"event_type": "e", "data": {}},
            {"guild_id": "g", "data": {}},
            {"guild_id": "g", "event_type": "e"},
        ],
        ids=["missing_guild_id", "missing_event_type", "missing_data"],
    )
    def test_missing_required_field_raises(self, payload):
        with pytest.raises(ValidationError):
            EventPayload.model_validate(payload)

    def test_non_dict_data_raises(self):
        with pytest.raises(ValidationError):
            EventPayload.model_validate(
                {"guild_id": "g", "event_type": "e", "data": ["not", "a", "dict"]}
            )

    def test_invalid_json_raises(self):
        with pytest.raises(ValidationError):
            EventPayload.model_validate_json(b"not json")


class TestEventStatus:
    def test_parses_from_stored_string_value(self):
        assert EventStatus("PENDING") is EventStatus.pending
        assert EventStatus("FAILED_DOWNSTREAM") is EventStatus.failed_downstream

    def test_unknown_value_raises(self):
        with pytest.raises(ValueError):
            EventStatus("NOT_A_STATUS")
