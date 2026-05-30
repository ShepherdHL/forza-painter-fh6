"""
Prevent mouse-wheel scrolling from changing Combobox/Listbox selections unless focused.

Without this, scrolling a panel often cycles readonly presets, filters, or list
selections when the pointer passes over a dropdown.
"""

from __future__ import annotations

import tkinter as tk

_WHEEL_SEQUENCES = ("<MouseWheel>", "<Button-4>", "<Button-5>")


def _focus_within_widget(widget: tk.Misc, focused: tk.Misc | None) -> bool:
    if focused is None:
        return False
    widget_name = str(widget)
    focused_name = str(focused)
    if focused_name == widget_name:
        return True
    return focused_name.startswith(widget_name + ".")


def _scroll_units(event: tk.Event) -> int:
    num = getattr(event, "num", None)
    if num == 4:
        return -1
    if num == 5:
        return 1
    try:
        return int(-1 * (event.delta / 120))
    except (AttributeError, TypeError, ValueError, tk.TclError):
        return 0


def _scroll_nearest_canvas(widget: tk.Misc, event: tk.Event) -> bool:
    parent = widget.master
    while parent is not None:
        if isinstance(parent, tk.Canvas):
            units = _scroll_units(event)
            if units:
                parent.yview_scroll(units, "units")
            return True
        try:
            parent = parent.master
        except (AttributeError, tk.TclError):
            break
    return False


def _wheel_selection_guard(event: tk.Event):
    widget = event.widget
    try:
        focused = widget.focus_get()
    except tk.TclError:
        focused = None
    if _focus_within_widget(widget, focused):
        return None
    _scroll_nearest_canvas(widget, event)
    return "break"


def install_scroll_selection_guards(root: tk.Misc) -> None:
    """Apply wheel guards to all ttk comboboxes and listboxes in this Tk instance."""
    for sequence in _WHEEL_SEQUENCES:
        root.bind_class("TCombobox", sequence, _wheel_selection_guard, add="+")
        root.bind_class("Listbox", sequence, _wheel_selection_guard, add="+")
