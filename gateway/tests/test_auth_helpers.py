"""Unit tests for the gateway's API-key helper functions."""

import hashlib

from main import _extract_api_key, _generate_api_key, _hash_api_key


class TestExtractApiKey:
    def test_returns_x_api_key_when_present(self):
        assert _extract_api_key("secret", None) == "secret"

    def test_x_api_key_takes_priority_over_bearer(self):
        assert _extract_api_key("header-key", "Bearer bearer-key") == "header-key"

    def test_strips_whitespace_from_x_api_key(self):
        assert _extract_api_key("  secret  ", None) == "secret"

    def test_whitespace_only_x_api_key_returns_none(self):
        assert _extract_api_key("   ", None) is None

    def test_falls_back_to_bearer_token(self):
        assert _extract_api_key(None, "Bearer secret") == "secret"

    def test_bearer_scheme_is_case_insensitive(self):
        assert _extract_api_key(None, "BEARER secret") == "secret"
        assert _extract_api_key(None, "bearer secret") == "secret"

    def test_strips_whitespace_from_bearer_token(self):
        assert _extract_api_key(None, "Bearer   secret  ") == "secret"

    def test_bearer_with_empty_token_returns_none(self):
        assert _extract_api_key(None, "Bearer   ") is None

    def test_non_bearer_authorization_returns_none(self):
        assert _extract_api_key(None, "Basic dXNlcjpwYXNz") is None

    def test_no_credentials_returns_none(self):
        assert _extract_api_key(None, None) is None


class TestHashApiKey:
    def test_is_deterministic(self):
        assert _hash_api_key("gwh_abc") == _hash_api_key("gwh_abc")

    def test_matches_sha256_hexdigest(self):
        expected = hashlib.sha256(b"gwh_abc").hexdigest()
        assert _hash_api_key("gwh_abc") == expected

    def test_different_keys_produce_different_hashes(self):
        assert _hash_api_key("gwh_one") != _hash_api_key("gwh_two")


class TestGenerateApiKey:
    def test_uses_default_prefix(self):
        assert _generate_api_key().startswith("gwh_")

    def test_uses_custom_prefix(self):
        assert _generate_api_key(prefix="custom").startswith("custom_")

    def test_generates_unique_keys(self):
        keys = {_generate_api_key() for _ in range(50)}
        assert len(keys) == 50

    def test_has_secret_material_after_prefix(self):
        secret = _generate_api_key().removeprefix("gwh_")
        assert len(secret) >= 24
