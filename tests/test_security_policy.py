"""Automated checks for security_policy limits and validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from security_policy import (
    ALLOWED_FETCH_HOSTS,
    GITHUB_RELEASES_API,
    MAX_GEOMETRY_JSON_BYTES,
    MAX_GEOMETRY_SHAPES,
    MAX_MEMORY_READ_BYTES,
    MAX_TEMPLATE_LAYER_COUNT,
    MIN_TEMPLATE_LAYER_COUNT,
    MIN_USER_ADDRESS,
    MAX_USER_ADDRESS,
    memory_addresses_allowed,
    manual_addresses_allowed,
    parse_safe_hex_address,
    redact_sensitive_log_text,
    trusted_locator_allowed,
    updates_enabled,
    validate_fetch_url,
    validate_fh6_session,
    validate_geometry_path,
    validate_template_layer_count,
    validate_user_address,
)


class TestAddressValidation:
    def test_accepts_user_range(self):
        assert validate_user_address(0x10000) == 0x10000
        assert validate_user_address("0x7FFFFFFFFFFF") == MAX_USER_ADDRESS

    def test_rejects_null_and_kernel_high(self):
        with pytest.raises(ValueError, match="user-mode range"):
            validate_user_address(0)
        with pytest.raises(ValueError, match="user-mode range"):
            validate_user_address(MAX_USER_ADDRESS + 1)

    def test_parse_safe_hex_address(self):
        assert parse_safe_hex_address("0x10000") == MIN_USER_ADDRESS
        assert parse_safe_hex_address("0x7FFFFFFFFFFF") == MAX_USER_ADDRESS
        assert parse_safe_hex_address("") is None
        with pytest.raises(ValueError, match="Invalid memory address format"):
            parse_safe_hex_address("not-an-address")
        with pytest.raises(ValueError, match="user-mode range"):
            parse_safe_hex_address("0x1")


class TestLayerCountLimits:
    def test_bounds(self):
        assert validate_template_layer_count(MIN_TEMPLATE_LAYER_COUNT) == MIN_TEMPLATE_LAYER_COUNT
        assert validate_template_layer_count(MAX_TEMPLATE_LAYER_COUNT) == MAX_TEMPLATE_LAYER_COUNT

    def test_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="between"):
            validate_template_layer_count(50)
        with pytest.raises(ValueError, match="between"):
            validate_template_layer_count(5000)


class TestGeometryFileLimits:
    def test_rejects_missing_file(self, tmp_path: Path):
        missing = tmp_path / "missing.json"
        with pytest.raises(ValueError, match="not found"):
            validate_geometry_path(missing)

    def test_rejects_oversized_file(self, tmp_path: Path):
        big = tmp_path / "big.json"
        big.write_text("x" * (MAX_GEOMETRY_JSON_BYTES + 1))
        with pytest.raises(ValueError, match="too large"):
            validate_geometry_path(big)


class TestFh6SessionValidation:
    def test_valid_session(self):
        session = {
            "type": "fh6_session_location_v1",
            "pid": 12345,
            "layer_count": 1000,
            "count_address": 0x10000,
            "table_address": 0x20000,
            "score": 0.95,
        }
        ok, reason = validate_fh6_session(session)
        assert ok, reason

    def test_rejects_wrong_type(self):
        ok, reason = validate_fh6_session({"type": "other", "pid": 1, "layer_count": 500, "count_address": 0x10000, "table_address": 0x20000})
        assert not ok
        assert "session type" in reason

    def test_rejects_bad_addresses(self):
        session = {
            "type": "fh6_session_location_v1",
            "pid": 1,
            "layer_count": 500,
            "count_address": 0x1,
            "table_address": 0x20000,
        }
        ok, reason = validate_fh6_session(session)
        assert not ok


class TestNetworkAllowlist:
    def test_github_api_allowed(self):
        assert validate_fetch_url(GITHUB_RELEASES_API) == GITHUB_RELEASES_API

    def test_rejects_http_and_unknown_hosts(self):
        with pytest.raises(ValueError, match="HTTPS"):
            validate_fetch_url("http://api.github.com/repos/x/releases/latest")
        with pytest.raises(ValueError, match="allowlist"):
            validate_fetch_url("https://evil.example.com/payload")

    def test_allowlist_is_minimal(self):
        assert ALLOWED_FETCH_HOSTS == frozenset(
            {"api.github.com", "raw.githubusercontent.com"}
        )


class TestEnvGates:
    def test_memory_addresses_require_explicit_env(self, monkeypatch):
        monkeypatch.delenv("FORZA_PAINTER_TRUSTED_LOCATOR", raising=False)
        monkeypatch.delenv("FORZA_PAINTER_ALLOW_MANUAL_ADDRESSES", raising=False)
        assert not memory_addresses_allowed()
        monkeypatch.setenv("FORZA_PAINTER_TRUSTED_LOCATOR", "1")
        assert memory_addresses_allowed()
        monkeypatch.delenv("FORZA_PAINTER_TRUSTED_LOCATOR", raising=False)
        monkeypatch.setenv("FORZA_PAINTER_ALLOW_MANUAL_ADDRESSES", "yes")
        assert manual_addresses_allowed()

    def test_updates_off_by_default(self, monkeypatch):
        monkeypatch.delenv("FORZA_PAINTER_CHECK_UPDATES", raising=False)
        assert not updates_enabled()
        monkeypatch.setenv("FORZA_PAINTER_CHECK_UPDATES", "1")
        assert updates_enabled()


class TestLogRedaction:
    def test_redacts_addresses_and_pid(self):
        text = "pid=12345 wrote 0x16debce3a9a table 0x20000"
        redacted = redact_sensitive_log_text(text)
        assert "12345" not in redacted
        assert "16debce3a9a" not in redacted
        assert "0x<redacted>" in redacted


class TestPolicyConstants:
    def test_sane_limits(self):
        assert MAX_GEOMETRY_SHAPES <= 5000
        assert MAX_MEMORY_READ_BYTES <= 128 * 1024 * 1024
        assert MIN_USER_ADDRESS >= 0x10000


class TestTrustWorkflowAdminCheck:
    def test_is_windows_admin_is_bool(self):
        from trust_workflow import is_windows_admin

        assert isinstance(is_windows_admin(), bool)

    def test_format_admin_action_label_adds_shield_when_not_admin(self, monkeypatch):
        from trust_workflow import ADMIN_SHIELD_PREFIX, format_admin_action_label

        monkeypatch.setattr("trust_workflow.is_windows_admin", lambda: False)
        assert format_admin_action_label("Import").startswith(ADMIN_SHIELD_PREFIX)

    def test_format_admin_action_label_plain_when_admin(self, monkeypatch):
        from trust_workflow import format_admin_action_label

        monkeypatch.setattr("trust_workflow.is_windows_admin", lambda: True)
        assert format_admin_action_label("Import") == "Import"
