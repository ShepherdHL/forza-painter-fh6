from __future__ import annotations

import tkinter as tk

from ui_input_guards import _focus_within_widget, _scroll_units


class _Widget:
    def __init__(self, name: str, master=None):
        self._name = name
        self.master = master

    def focus_get(self):
        return self

    def __str__(self):
        return self._name


def test_focus_within_widget_matches_self_and_children():
    combo = _Widget(".!combobox")
    entry = _Widget(".!combobox.!entry", combo)
    assert _focus_within_widget(combo, combo)
    assert _focus_within_widget(combo, entry)
    assert not _focus_within_widget(combo, _Widget(".!other"))


def test_scroll_units_mousewheel():
    event = tk.Event()
    event.delta = 120
    assert _scroll_units(event) == -1
