"""User-visible trust workflow: consent, elevation, and helper command disclosure."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from tkinter import BOTH, Button, Frame, Label, Text, Toplevel, X, LEFT, RIGHT, messagebox

from app_config import MEMORY_WORK_CONSENT_FLAG
from security_policy import redact_sensitive_log_text

TranslateFn = Callable[[str, str], str]

HELPER_LABELS = {
    "main": "geometry importer",
    "fh6_probe": "FH6 memory locator / diagnostics",
    "fh6_import_typecode_json": "handmade JSON importer",
    "fh6_export_typecode_json": "handmade JSON exporter",
    "fh6_trim_group_count": "vinyl group layer-count trim",
}

# UAC-style hint: shown on buttons when the process is not elevated.
ADMIN_SHIELD_PREFIX = "\U0001f6e1 "  # 🛡️

# Translation keys for buttons that call prepare_memory_work / OpenProcess.
ADMIN_ACTION_KEYS = frozenset(
    {
        "import_final_import",
        "handmade_import",
        "export_game_json",
        "auto_locate",
        "diagnose",
        "save_snapshot",
        "compare_snapshot",
        "inspect_table",
    }
)


def action_requires_admin(key: str) -> bool:
    return str(key) in ADMIN_ACTION_KEYS


def format_admin_action_label(text: str, *, requires_admin: bool = True) -> str:
    """Prefix label with a shield when elevation will be required."""
    if not requires_admin or is_windows_admin():
        return text
    if text.startswith(ADMIN_SHIELD_PREFIX):
        return text
    return f"{ADMIN_SHIELD_PREFIX}{text}"


def is_windows_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def request_admin_restart() -> None:
    """Re-launch this executable with UAC elevation and exit the current process."""
    try:
        from build_profile import elevation_disabled
    except Exception:
        elevation_disabled = lambda: False  # type: ignore

    if elevation_disabled():
        try:
            from defender_audit import log_elevation

            log_elevation("elevation blocked by build profile")
        except Exception:
            pass
        return

    try:
        from defender_audit import log_elevation

        log_elevation("ShellExecuteW runas", argv=subprocess.list2cmdline(sys.argv))
    except Exception:
        pass
    params = subprocess.list2cmdline(sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    raise SystemExit(0)


def memory_consent_granted() -> bool:
    try:
        return MEMORY_WORK_CONSENT_FLAG.is_file()
    except OSError:
        return False


def persist_memory_consent() -> None:
    try:
        MEMORY_WORK_CONSENT_FLAG.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_WORK_CONSENT_FLAG.write_text("granted\n", encoding="utf-8")
    except OSError:
        pass


def helper_name_from_command(cmd: Sequence) -> str:
    parts = [str(x) for x in cmd]
    if len(parts) >= 3 and parts[1] == "--helper":
        return parts[2]
    for part in parts:
        name = Path(part).name.lower()
        if name.endswith(".py"):
            return Path(part).stem
    return "task"


def describe_helper_launch(cmd: Sequence) -> str:
    name = helper_name_from_command(cmd)
    label = HELPER_LABELS.get(name, name)
    redacted = redact_sensitive_log_text(subprocess.list2cmdline([str(x) for x in cmd]))
    return (
        f"Starting helper: {label} (same application, helper mode). "
        f"Command: {redacted}"
    )


def is_permission_error_text(text: str) -> bool:
    lower = (text or "").lower()
    return any(
        token in lower
        for token in (
            "access is denied",
            "winerror 5",
            "permissionerror",
            "unable to open forza process",
            "run the app as administrator",
            "run this app as administrator",
        )
    )


def show_elevation_prompt(root, tr: TranslateFn, lang: str) -> bool:
    return messagebox.askyesno(
        tr(lang, "elevate_prompt_title"),
        tr(lang, "elevate_prompt_message"),
        parent=root,
    )


def show_memory_work_consent(
    root,
    tr: TranslateFn,
    lang: str,
    *,
    operation: str,
    game_label: str,
    process_name: str,
    pid: int,
) -> bool:
    if memory_consent_granted():
        return True

    from ui.dialog_theme import (
        resolve_tokens,
        style_body_text,
        style_dialog_button,
        style_frame,
        style_heading_label,
        style_toplevel,
    )

    tokens = resolve_tokens(root)
    dialog = Toplevel(root)
    dialog.title(tr(lang, f"memory_consent_title_{operation}"))
    dialog.transient(root)
    dialog.grab_set()
    style_toplevel(dialog, tokens)

    body = Frame(dialog, bg=tokens.dialog_bg, padx=16, pady=12)
    body.pack(fill=BOTH, expand=True)
    style_frame(body, tokens)

    title = Label(
        body,
        text=tr(lang, f"memory_consent_title_{operation}"),
        anchor="w",
        justify="left",
        wraplength=520,
    )
    style_heading_label(title, tokens, font=("Segoe UI", 12, "bold"))
    title.pack(fill=X, pady=(0, 8))

    text = Text(body, height=14, width=72, wrap="word", padx=8, pady=8)
    style_body_text(text, tokens)
    text.pack(fill=BOTH, expand=True)
    message = tr(lang, "memory_consent_body").format(
        game=game_label,
        process=process_name,
        pid=pid,
        operation=tr(lang, f"memory_consent_operation_{operation}"),
    )
    text.insert("1.0", message)
    text.config(state="disabled")

    actions = Frame(body, bg=tokens.dialog_bg)
    actions.pack(fill=X, pady=(10, 0))
    style_frame(actions, tokens)

    result = {"ok": False}

    def accept() -> None:
        result["ok"] = True
        persist_memory_consent()
        dialog.destroy()

    def cancel() -> None:
        dialog.destroy()

    def open_safety() -> None:
        from ui.safety_viewer import show_safety_guide

        show_safety_guide(root, tr, lang, ask_language=True)

    safety_btn = Button(actions, text=tr(lang, "memory_consent_open_safety"), command=open_safety)
    style_dialog_button(safety_btn, tokens)
    safety_btn.pack(side=LEFT)
    cancel_btn = Button(actions, text=tr(lang, "memory_consent_cancel"), command=cancel)
    style_dialog_button(cancel_btn, tokens)
    cancel_btn.pack(side=RIGHT, padx=(6, 0))
    continue_btn = Button(actions, text=tr(lang, "memory_consent_continue"), command=accept)
    style_dialog_button(continue_btn, tokens)
    continue_btn.pack(side=RIGHT)

    dialog.update_idletasks()
    try:
        dialog.minsize(560, 420)
    except Exception:
        pass
    dialog.wait_window()
    return bool(result["ok"])


def prepare_memory_work(
    root,
    tr: TranslateFn,
    lang: str,
    *,
    operation: str,
    game_label: str,
    process_name: str,
    pid: int,
) -> bool:
    """Consent + ensure administrator before FH6 memory attach. May restart the app."""
    if not show_memory_work_consent(
        root,
        tr,
        lang,
        operation=operation,
        game_label=game_label,
        process_name=process_name,
        pid=pid,
    ):
        return False
    if is_windows_admin():
        return True
    try:
        from build_profile import elevation_disabled
    except Exception:
        elevation_disabled = lambda: False  # type: ignore

    if elevation_disabled():
        return True
    if not show_elevation_prompt(root, tr, lang):
        return False
    request_admin_restart()
    return False
