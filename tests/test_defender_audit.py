"""Tests for defender_audit behavior logging."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def audit_log(tmp_path: Path, monkeypatch):
    log_file = tmp_path / "defender-audit.log"
    monkeypatch.setenv("FORZA_PAINTER_DEFENDER_AUDIT", "1")
    import defender_audit as audit

    monkeypatch.setattr(audit, "_LOG_PATH", log_file)
    monkeypatch.setattr(audit, "_ENABLED", True)
    return log_file, audit


def test_audit_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FORZA_PAINTER_DEFENDER_AUDIT", raising=False)
    import defender_audit as audit

    audit._ENABLED = None
    assert not audit.audit_enabled()


def test_log_event_writes_category(audit_log):
    log_file, audit = audit_log
    audit.log_event(audit.CATEGORY_ELEVATION, "test elevation", detail="x")
    text = log_file.read_text(encoding="utf-8")
    assert "[ELEVATION]" in text
    assert "test elevation" in text


def test_log_subprocess_redacts_addresses(audit_log, monkeypatch):
    log_file, audit = audit_log
    monkeypatch.setenv("FORZA_PAINTER_REDACT_LOGS", "1")
    audit.log_subprocess(
        ["python.exe", "--helper", "main", "--pid", "12345", "0x16debce3a9a"],
        purpose="helper",
    )
    text = log_file.read_text(encoding="utf-8")
    assert "PROCESS_SPAWN" in text
    assert "12345" not in text
    assert "16debce3a9a" not in text
