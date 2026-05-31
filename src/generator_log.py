"""Parse bundled generator stdout into user-facing log lines."""

from __future__ import annotations

import re


def friendly_generator_line(line: str | None) -> str | None:
    text = (line or "").strip()
    if not text:
        return None
    progress = re.match(r"\[(\d+)/(\d+)\]\s+(.*)", text)
    if progress:
        current, total, detail = progress.groups()
        lowered = detail.lower()
        if "saved geometry checkpoint" in lowered:
            return f"Saved JSON checkpoint {current}/{total}"
        if "saved preview snapshot" in lowered:
            return f"Updated preview {current}/{total}"
        if "step completed" in lowered:
            return None
        return f"Generated layer {current}/{total}"
    if text.startswith("Loaded image:"):
        return text
    if text.startswith("Settings:"):
        return text
    if text.startswith("OpenCL: Selected device"):
        return text
    if text.startswith("Vulkan:"):
        return text
    if text.startswith("Scoring mode:"):
        return text
    if text in ("FINISHED",):
        return text
    lowered = text.lower()
    if re.search(r"errorgridsize|error[-_\s]?grid", lowered):
        return None
    if re.search(r"\b(error|failed|panic)\b", lowered):
        return text
    return None
