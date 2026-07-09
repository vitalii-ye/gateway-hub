"""Tests for handle_message: ack/nack decisions, statuses, and audit logging."""

import httpx
import pytest
from conftest import FakeDiscordBotClient, FakeStores, make_event, make_message
from main import handle_message

from shared.models import EventStatus, GuildConfig, Rule, RuleAction

GUILD_ID = "guild-123"


def guild_config_with_send_message(
    channel_id: str = "ch-1",
    content: str = "{{username}} bought {{item}}",
    event_type: str = "item_purchased",
) -> GuildConfig:
    return GuildConfig(
        rules=[
            Rule(
                event_type=event_type,
                actions=[
                    RuleAction(
                        type="SEND_MESSAGE", channel_id=channel_id, content=content
                    )
                ],
            )
        ]
    )


@pytest.fixture
def stores() -> FakeStores:
    return FakeStores(guild_configs={GUILD_ID: guild_config_with_send_message()})


def http_error(status_code: int = 500) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://discord-bot:9000/v1/messages")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"{status_code} error", request=request, response=response
    )


class TestHappyPath:
    async def test_sends_rendered_message_to_discord(self, stores, discord):
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert discord.executed == [
            {"channel_id": "ch-1", "content": "alice bought sword"}
        ]

    async def test_marks_event_processed_and_acks(self, stores, discord):
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.processed}
        assert message.acked is True
        assert message.nacked_requeue is None
        assert message.rejected_requeue is None

    async def test_appends_audit_log_entry(self, stores, discord):
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        entries = stores.audit_logs[GUILD_ID]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["event_id"] == "evt-1"
        assert entry["guild_id"] == GUILD_ID
        assert entry["outcome"] == EventStatus.processed.value
        assert entry["actions"] == [
            {
                "type": "SEND_MESSAGE",
                "channel_id": "ch-1",
                "content": "{{username}} bought {{item}}",
            }
        ]

    async def test_multiple_matching_rules_send_multiple_messages(self, discord):
        cfg = GuildConfig(
            rules=[
                Rule(
                    event_type="item_purchased",
                    actions=[
                        RuleAction(type="SEND_MESSAGE", channel_id="ch-1", content="a")
                    ],
                ),
                Rule(
                    event_type="item_purchased",
                    actions=[
                        RuleAction(type="SEND_MESSAGE", channel_id="ch-2", content="b")
                    ],
                ),
            ]
        )
        stores = FakeStores(guild_configs={GUILD_ID: cfg})
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert [p["channel_id"] for p in discord.executed] == ["ch-1", "ch-2"]
        assert stores.statuses["evt-1"] == EventStatus.processed


class TestPoisonMessages:
    async def test_missing_event_id_header_rejects_without_requeue(
        self, stores, discord
    ):
        message = make_message(make_event(guild_id=GUILD_ID), event_id=None)

        await handle_message(message, stores=stores, discord=discord)

        assert message.rejected_requeue is False
        assert message.acked is False
        assert stores.statuses == {}
        assert discord.executed == []

    async def test_non_string_event_id_header_rejects_without_requeue(
        self, stores, discord
    ):
        message = make_message(make_event(guild_id=GUILD_ID), event_id=12345)

        await handle_message(message, stores=stores, discord=discord)

        assert message.rejected_requeue is False
        assert stores.statuses == {}

    async def test_invalid_payload_marks_failed_invalid_payload_and_acks(
        self, stores, discord
    ):
        message = make_message(body=b'{"not": "an event payload"}')

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_invalid_payload}
        assert message.acked is True
        assert discord.executed == []

    async def test_non_json_body_marks_failed_invalid_payload_and_acks(
        self, stores, discord
    ):
        message = make_message(body=b"not json at all")

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_invalid_payload}
        assert message.acked is True


class TestIgnoredOutcomes:
    async def test_no_guild_config_marks_ignored_no_config_and_acks(self, discord):
        stores = FakeStores(guild_configs={})
        message = make_message(make_event(guild_id="unknown-guild"))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.ignored_no_config}
        assert message.acked is True
        assert discord.executed == []
        assert stores.audit_logs == {}

    async def test_no_rule_match_marks_ignored_no_match_and_acks(self, stores, discord):
        message = make_message(
            make_event(guild_id=GUILD_ID, event_type="unmatched_event")
        )

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.ignored_no_match}
        assert message.acked is True
        assert discord.executed == []
        entry = stores.audit_logs[GUILD_ID][0]
        assert entry["outcome"] == EventStatus.ignored_no_match.value
        assert entry["event"]["event_type"] == "unmatched_event"


class TestFailures:
    async def test_discord_http_error_marks_failed_downstream_and_nacks_with_requeue(
        self, stores
    ):
        discord = FakeDiscordBotClient(error=http_error(500))
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_downstream}
        assert message.nacked_requeue is True
        assert message.acked is False

    async def test_discord_connect_error_marks_failed_downstream_and_nacks(
        self, stores
    ):
        discord = FakeDiscordBotClient(error=httpx.ConnectError("connection refused"))
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_downstream}
        assert message.nacked_requeue is True

    async def test_matching_action_without_channel_marks_failed_processing_and_acks(
        self, discord
    ):
        cfg = guild_config_with_send_message(channel_id=None)
        stores = FakeStores(guild_configs={GUILD_ID: cfg})
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_processing}
        assert message.acked is True
        assert discord.executed == []
        entry = stores.audit_logs[GUILD_ID][0]
        assert entry["outcome"] == EventStatus.failed_processing.value

    async def test_unexpected_error_marks_failed_processing_and_nacks_with_requeue(
        self, stores, discord
    ):
        discord.error = RuntimeError("boom")
        message = make_message(make_event(guild_id=GUILD_ID))

        await handle_message(message, stores=stores, discord=discord)

        assert stores.statuses == {"evt-1": EventStatus.failed_processing}
        assert message.nacked_requeue is True
        assert message.acked is False
