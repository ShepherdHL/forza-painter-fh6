"""Ensure UI modules import tkinter layout constants they reference by name."""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"

# Bare names such as pack(fill=X) — not string literals like fill="x".
TK_LAYOUT_CONSTANTS = frozenset(
    {
        "X",
        "Y",
        "BOTH",
        "LEFT",
        "RIGHT",
        "TOP",
        "BOTTOM",
        "END",
        "HORIZONTAL",
        "VERTICAL",
        "NW",
        "NE",
        "SW",
        "SE",
        "N",
        "S",
        "E",
        "W",
        "NS",
        "EW",
        "NSEW",
        "CENTER",
    }
)


def _tkinter_imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "tkinter":
            for alias in node.names:
                names.add(alias.asname or alias.name)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tkinter":
                    names.add(alias.asname or "tkinter")
    return names


def _bare_tk_constant_uses(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in TK_LAYOUT_CONSTANTS:
            used.add(node.id)
    return used


def _collect_missing_imports() -> list[str]:
    messages: list[str] = []
    ui_paths = [SRC_ROOT / "app.py", *SRC_ROOT.glob("ui_*.py"), *SRC_ROOT.glob("ui/**/*.py")]
    for path in sorted(set(ui_paths)):
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imported = _tkinter_imported_names(tree)
        used = _bare_tk_constant_uses(tree)
        missing = sorted(used - imported)
        if missing:
            rel = path.relative_to(SRC_ROOT.parent)
            messages.append(
                f"{rel}: uses {missing!r} without importing from tkinter"
            )
    return messages


def test_tk_layout_constants_are_imported() -> None:
    messages = _collect_missing_imports()
    assert not messages, (
        "Missing tkinter layout constant imports:\n"
        + "\n".join(messages)
        + "\nImport from tkinter or ui.tk_layout (e.g. from ui.tk_layout import X, BOTH)."
    )
