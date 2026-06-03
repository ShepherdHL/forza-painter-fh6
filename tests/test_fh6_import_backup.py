"""Tests for compact type-code import backup format."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fh6_import_typecode_json import _backup_layer_entry


def test_backup_layer_entry_uses_base64_without_decoded() -> None:
    raw = b"\x01" * 0x140
    entry = _backup_layer_entry(3, 0x12345678, raw)
    assert entry["index"] == 3
    assert entry["ptr"] == "0x12345678"
    assert "raw_hex" not in entry
    assert "decoded" not in entry
    assert base64.b64decode(entry["raw_b64"]) == raw


def test_backup_layer_entry_partial_flag() -> None:
    entry = _backup_layer_entry(1, 0x10, b"\x00" * 0x80, partial=True)
    assert entry["partial"] is True
