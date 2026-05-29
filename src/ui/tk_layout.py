"""Tkinter pack/grid constants for UI modules.

Import layout constants from this module (or from ``tkinter`` directly) so names
like ``X`` and ``BOTH`` are always defined. A repo test scans for bare uses of
these names without a matching import — missing imports cause startup NameError.
"""

from tkinter import BOTH, BOTTOM, END, HORIZONTAL, LEFT, RIGHT, TOP, VERTICAL, X, Y

__all__ = [
    "BOTH",
    "BOTTOM",
    "END",
    "HORIZONTAL",
    "LEFT",
    "RIGHT",
    "TOP",
    "VERTICAL",
    "X",
    "Y",
]
