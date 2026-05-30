"""
Experimental per-image generator presets derived from Image Preview complexity estimates.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from app_paths import RESOURCE_ROOT, ROOT
from preset_preview import effective_max_dimension

SETTING_KEYS: tuple[str, ...] = (
    "maxPreviewSize",
    "maxResolution",
    "maxThreads",
    "mutatedSamples",
    "enableProgressiveSampling",
    "progressiveSamplingStart",
    "progressiveSamplingEnd",
    "progressiveSamplingTransition",
    "progressiveSamplingCurve",
    "errorGridSize",
    "forceOpaqueShapes",
    "posterizeLevels",
    "previewEvery",
    "randomSamples",
    "preprocessMode",
    "saveAt",
    "saveEvery",
    "stopAt",
)

BUNDLED_SETTINGS_DIR = RESOURCE_ROOT / "config" / "settings"

IMAGE_PROFILES_DIR = ROOT / "runtime" / "image-profiles"
ACTIVE_PROFILE_PATH = IMAGE_PROFILES_DIR / "tailored-active.ini"
TAILORED_SETTINGS_PATH = ROOT / "runtime" / "settings" / "tailored_preset.json"
TAILORED_BADGE = "🧪▃▃"
TAILORED_DISPLAY_NAME = "Tailored"
NORMAL_PRESET_FRAGMENT = "normal.ini"

MIN_STOP_AT = 100
MAX_STOP_AT = 3000
LAYER_SNAP = 50


def is_tailored_experimental_preset(setting) -> bool:
    if setting is None:
        return False
    source = setting.get("source") if hasattr(setting, "get") else setting["source"]
    return source == "tailored"


def _normal_preset_path() -> Path | None:
    if not BUNDLED_SETTINGS_DIR.is_dir():
        return None
    for path in sorted(BUNDLED_SETTINGS_DIR.glob("*.ini")):
        if NORMAL_PRESET_FRAGMENT in path.name.lower():
            return path
    return None


def _parse_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def normal_base_values() -> dict[str, str]:
    path = _normal_preset_path()
    if path is None:
        return {}
    return _parse_settings(path)


def image_profile_key(image_path: Path) -> str:
    try:
        resolved = str(image_path.expanduser().resolve()).lower()
    except OSError:
        resolved = str(image_path).lower()
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]


def profile_path_for_key(key: str) -> Path:
    return IMAGE_PROFILES_DIR / f"{key}.ini"


def snap_layers_up(value: int, step: int = LAYER_SNAP) -> int:
    value = max(MIN_STOP_AT, int(value))
    return min(MAX_STOP_AT, ((value + step - 1) // step) * step)


def compute_stop_at(complexity_estimate: int) -> int:
    target = max(MIN_STOP_AT, int(math.ceil(complexity_estimate * 1.25)))
    return snap_layers_up(target)


def compute_random_samples(stop_at: int) -> int:
    if stop_at <= 500:
        return 45_000
    if stop_at <= 1000:
        return 75_000
    if stop_at <= 1800:
        return 120_000
    if stop_at <= 2500:
        return 180_000
    return 220_000


def compute_save_at(stop_at: int, save_every: int = 50) -> str:
    save_every = max(10, int(save_every))
    points: list[int] = []
    value = save_every
    while value < stop_at:
        points.append(value)
        value += save_every
    if not points or points[-1] != stop_at:
        points.append(stop_at)
    return ",".join(str(point) for point in points)


def compute_max_resolution(width: int, height: int, *, cap: int = 1400) -> int:
    if width <= 0 or height <= 0:
        return cap
    longest = max(width, height)
    return max(640, min(cap, longest))


def build_tailored_values(
    *,
    complexity_estimate: int,
    width: int,
    height: int,
    preprocess_mode: str,
    base_values: dict[str, str] | None = None,
) -> dict[str, str]:
    base = dict(base_values or normal_base_values())
    stop_at = compute_stop_at(complexity_estimate)
    save_every = 50
    try:
        save_every = max(10, int(str(base.get("saveEvery", save_every)).strip()))
    except (TypeError, ValueError):
        save_every = 50
    eff_w, eff_h = effective_max_dimension(width, height, compute_max_resolution(width, height))
    max_resolution = max(eff_w, eff_h)
    values = dict(base)
    values["displayName"] = TAILORED_DISPLAY_NAME
    values["stopAt"] = str(stop_at)
    values["saveAt"] = compute_save_at(stop_at, save_every)
    values["saveEvery"] = str(save_every)
    values["randomSamples"] = str(compute_random_samples(stop_at))
    values["maxResolution"] = str(max_resolution)
    values["preprocessMode"] = preprocess_mode
    return values


def _write_ini(path: Path, values: dict[str, str], *, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"description = {description}"]
    for key in SETTING_KEYS:
        if key in values:
            lines.append(f"{key} = {values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tailored_profile(
    image_path: Path,
    values: dict[str, str],
    *,
    complexity_estimate: int,
    image_name: str,
) -> Path:
    IMAGE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    key = image_profile_key(image_path)
    description = (
        f"Tailored preset for {image_name} "
        f"(complexity est. ~{complexity_estimate}, cap {values.get('stopAt', '?')} layers). "
        "Approximate — results may vary."
    )
    per_image = profile_path_for_key(key)
    _write_ini(per_image, values, description=description)
    _write_ini(ACTIVE_PROFILE_PATH, values, description=description)
    meta = {
        "image_key": key,
        "image_name": image_name,
        "complexity_estimate": complexity_estimate,
        "stop_at": int(values.get("stopAt", 0)),
    }
    try:
        TAILORED_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TAILORED_SETTINGS_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return ACTIVE_PROFILE_PATH


def tailored_profile_metadata() -> dict[str, Any]:
    if not TAILORED_SETTINGS_PATH.is_file():
        return {}
    try:
        payload = json.loads(TAILORED_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_tailored_setting_profile():
    from generator_backend import SettingProfile
    from preset_preview import preset_label_with_badge

    if not ACTIVE_PROFILE_PATH.is_file():
        return None
    values = _parse_settings(ACTIVE_PROFILE_PATH)
    if not values:
        return None
    description = setting_description(ACTIVE_PROFILE_PATH)
    display = str(values.get("displayName", "")).strip() or TAILORED_DISPLAY_NAME
    label = preset_label_with_badge(f"0. {display}", TAILORED_BADGE)
    return SettingProfile(
        index=0,
        source="tailored",
        path=ACTIVE_PROFILE_PATH,
        label=label,
        description=description,
        values=values,
        badge_prefix=TAILORED_BADGE,
    )


def tailored_placeholder_profile():
    from generator_backend import SettingProfile
    from preset_preview import preset_label_with_badge

    values = normal_base_values()
    values["displayName"] = TAILORED_DISPLAY_NAME
    description = (
        "Per-image preset (opt-in, not the default). "
        "Add an image on Generate or Image Preview to build slot 0; keep Normal for routine runs."
    )
    label = preset_label_with_badge(f"0. {TAILORED_DISPLAY_NAME}", TAILORED_BADGE)
    return SettingProfile(
        index=0,
        source="tailored",
        path=ACTIVE_PROFILE_PATH,
        label=label,
        description=description,
        values=values,
        badge_prefix=TAILORED_BADGE,
    )


def setting_description(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("description"):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def load_tailored_acknowledged(root: Path | None = None) -> bool:
    path = (root or ROOT) / "runtime" / "settings" / "tailored_preset_ack.json"
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return bool(payload.get("acknowledged"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False


def save_tailored_acknowledged(acknowledged: bool, root: Path | None = None) -> None:
    path = (root or ROOT) / "runtime" / "settings" / "tailored_preset_ack.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"acknowledged": acknowledged}, indent=2) + "\n", encoding="utf-8")


def renumber_bundled_profile_label(profile):
    from generator_backend import SettingProfile
    from preset_preview import preset_badge_prefix, preset_label_with_badge

    preset_index = _preset_index_from_path(profile.path)
    display = str(profile.values.get("displayName", "")).strip()
    if not display:
        display = _preset_stem_name(profile.path)
        if profile.source == "user":
            display = f"User / {display}"
    display_index = (preset_index + 1) if preset_index is not None else profile.index + 1
    base_label = f"{display_index}. {display}"
    badge = profile.badge_prefix or preset_badge_prefix(
        profile.path, profile.values, preset_index=preset_index
    )
    return SettingProfile(
        index=profile.index,
        source=profile.source,
        path=profile.path,
        label=preset_label_with_badge(base_label, badge),
        description=profile.description,
        values=profile.values,
        badge_prefix=badge,
    )


def _preset_index_from_path(path: Path) -> int | None:
    match = re.match(r"^(\d+)", path.stem)
    return int(match.group(1)) if match else None


def _preset_stem_name(path: Path) -> str:
    name = re.sub(r"^\d+[.)]\s*", "", path.stem, flags=re.IGNORECASE)
    return name.replace(" - ", " / ")
