"""PresetCombobox chrome (dropdown affordance)."""

from __future__ import annotations

import tkinter as tk
from tkinter import StringVar

from ui.preset_combobox import PresetComboItem, PresetCombobox


def test_preset_combobox_has_bordered_shell_and_chevron():
    root = tk.Tk()
    root.withdraw()
    try:
        var = StringVar(value="3. Normal")
        combo = PresetCombobox(root, var)
        combo.set_items([PresetComboItem(label="3. Normal", fg="#0088cc")])
        combo.update_idletasks()
        assert combo._shell.winfo_exists()
        assert combo._chevron.cget("text") == "▾"
        assert int(combo._shell.cget("highlightthickness")) == 1
    finally:
        root.destroy()
