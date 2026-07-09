"""Unit tests for the rules-engine's pure evaluation and rendering functions."""

from conftest import make_event
from main import _get_by_path, _render_message_template, _rule_matches, evaluate_rules

from shared.models import GuildConfig, Rule, RuleAction


class TestGetByPath:
    def test_returns_top_level_value(self):
        assert _get_by_path({"guild_id": "g-1"}, "guild_id") == "g-1"

    def test_returns_nested_value(self):
        obj = {"data": {"item": "sword"}}

        assert _get_by_path(obj, "data.item") == "sword"

    def test_returns_deeply_nested_value(self):
        obj = {"data": {"player": {"name": "alice"}}}

        assert _get_by_path(obj, "data.player.name") == "alice"

    def test_missing_top_level_key_returns_none(self):
        assert _get_by_path({"data": {}}, "missing") is None

    def test_missing_nested_key_returns_none(self):
        assert _get_by_path({"data": {"item": "sword"}}, "data.amount") is None

    def test_non_dict_intermediate_returns_none(self):
        obj = {"data": {"item": "sword"}}

        assert _get_by_path(obj, "data.item.name") is None

    def test_non_dict_root_returns_none(self):
        assert _get_by_path("not-a-dict", "data.item") is None

    def test_none_value_at_path_returns_none(self):
        assert _get_by_path({"data": {"item": None}}, "data.item") is None


class TestRuleMatches:
    def test_matches_on_event_type_with_no_conditions(self):
        rule = Rule(event_type="item_purchased")

        assert _rule_matches(make_event(), rule) is True

    def test_event_type_mismatch_returns_false(self):
        rule = Rule(event_type="player_joined")

        assert _rule_matches(make_event(event_type="item_purchased"), rule) is False

    def test_condition_on_data_path_matches(self):
        rule = Rule(event_type="item_purchased", conditions={"data.item": "sword"})

        assert _rule_matches(make_event(data={"item": "sword"}), rule) is True

    def test_condition_value_mismatch_returns_false(self):
        rule = Rule(event_type="item_purchased", conditions={"data.item": "shield"})

        assert _rule_matches(make_event(data={"item": "sword"}), rule) is False

    def test_condition_on_missing_path_returns_false(self):
        rule = Rule(event_type="item_purchased", conditions={"data.rarity": "epic"})

        assert _rule_matches(make_event(data={"item": "sword"}), rule) is False

    def test_all_of_multiple_conditions_must_match(self):
        rule = Rule(
            event_type="item_purchased",
            conditions={"data.item": "sword", "data.user_id": "42"},
        )

        matching = make_event(data={"item": "sword", "user_id": "42"})
        partial = make_event(data={"item": "sword", "user_id": "99"})

        assert _rule_matches(matching, rule) is True
        assert _rule_matches(partial, rule) is False

    def test_condition_on_top_level_field(self):
        rule = Rule(event_type="item_purchased", conditions={"guild_id": "guild-123"})

        assert _rule_matches(make_event(guild_id="guild-123"), rule) is True
        assert _rule_matches(make_event(guild_id="other"), rule) is False


class TestEvaluateRules:
    def test_no_rules_returns_empty_list(self):
        assert evaluate_rules(make_event(), GuildConfig(rules=[])) == []

    def test_no_matching_rule_returns_empty_list(self):
        cfg = GuildConfig(rules=[Rule(event_type="player_joined")])

        assert evaluate_rules(make_event(event_type="item_purchased"), cfg) == []

    def test_matching_rule_returns_its_actions(self):
        action = RuleAction(type="SEND_MESSAGE", channel_id="ch-1", content="hi")
        cfg = GuildConfig(rules=[Rule(event_type="item_purchased", actions=[action])])

        assert evaluate_rules(make_event(), cfg) == [action]

    def test_actions_from_multiple_matching_rules_accumulate_in_order(self):
        first = RuleAction(type="SEND_MESSAGE", channel_id="ch-1", content="first")
        second = RuleAction(type="SEND_MESSAGE", channel_id="ch-2", content="second")
        cfg = GuildConfig(
            rules=[
                Rule(event_type="item_purchased", actions=[first]),
                Rule(event_type="player_joined", actions=[]),
                Rule(event_type="item_purchased", actions=[second]),
            ]
        )

        assert evaluate_rules(make_event(), cfg) == [first, second]

    def test_non_matching_rules_contribute_no_actions(self):
        matching = RuleAction(type="SEND_MESSAGE", channel_id="ch-1", content="yes")
        cfg = GuildConfig(
            rules=[
                Rule(
                    event_type="item_purchased",
                    conditions={"data.item": "shield"},
                    actions=[
                        RuleAction(type="SEND_MESSAGE", channel_id="ch-9", content="no")
                    ],
                ),
                Rule(event_type="item_purchased", actions=[matching]),
            ]
        )

        assert evaluate_rules(make_event(data={"item": "sword"}), cfg) == [matching]


class TestRenderMessageTemplate:
    def test_renders_all_placeholders(self):
        event = make_event(
            guild_id="guild-123",
            event_type="item_purchased",
            data={"item": "sword", "user_id": "42", "username": "alice"},
        )
        template = (
            "{{username}} ({{user_id}}) bought {{item}} [{{event_type}} @ {{guild_id}}]"
        )

        rendered = _render_message_template(template, event)

        assert rendered == "alice (42) bought sword [item_purchased @ guild-123]"

    def test_missing_data_keys_render_as_empty_string(self):
        event = make_event(data={})

        rendered = _render_message_template("item={{item}} user={{username}}", event)

        assert rendered == "item= user="

    def test_template_without_placeholders_is_unchanged(self):
        rendered = _render_message_template("static message", make_event())

        assert rendered == "static message"

    def test_repeated_placeholder_is_replaced_everywhere(self):
        event = make_event(data={"item": "sword"})

        rendered = _render_message_template("{{item}} and {{item}}", event)

        assert rendered == "sword and sword"

    def test_non_string_data_values_are_stringified(self):
        event = make_event(data={"item": 7, "user_id": 42})

        rendered = _render_message_template("{{item}}/{{user_id}}", event)

        assert rendered == "7/42"

    def test_unknown_placeholders_are_left_intact(self):
        rendered = _render_message_template("{{unknown}}", make_event())

        assert rendered == "{{unknown}}"
