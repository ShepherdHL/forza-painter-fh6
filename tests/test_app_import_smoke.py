"""Ensure app.py imports (catches missing imports before class body is defined)."""

import pytest

psutil = pytest.importorskip("psutil")


def test_app_module_imports():
    import app  # noqa: F401

    assert hasattr(app, "App")
    assert hasattr(app, "main")
