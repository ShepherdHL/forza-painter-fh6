"""
Discover CJK-capable fonts on the local machine and validate glyph coverage.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from mandarin_chars import is_cjk_char, is_hangul_char, text_contains_hangul, text_scripts, unique_chars

_FONT_EXTS = {".ttf", ".ttc", ".otf", ".fon"}
_PROBE_SIZE = 48
_PROBE_CHARS = "中文测试ソニック가"

_SC_HINTS = (
    "yahei",
    "simhei",
    "simsun",
    "simkai",
    "dengxian",
    "noto sans sc",
    "noto sans cjk sc",
    "source han sans sc",
    "source han sans cn",
    "pingfang sc",
    "stkaiti",
    "fangsong",
)
_TC_HINTS = (
    "mingliu",
    "pmingliu",
    "microsoft jhenghei",
    "kaiti tc",
    "noto sans tc",
    "noto sans cjk tc",
    "pingfang tc",
)
_JP_HINTS = ("meiryo", "yu goth", "msgothic", "ms gothic", "ms mincho", "noto sans jp", "noto sans cjk jp")
_KR_HINTS = ("malgun", "gulim", "dotum", "batang", "noto sans kr", "noto sans cjk kr")
_CJK_HINTS = _SC_HINTS + _TC_HINTS + _JP_HINTS + _KR_HINTS

SCRIPT_UNIVERSAL = "universal"
SCRIPT_JAPANESE = "japanese"
SCRIPT_KOREAN = "korean"
SCRIPT_CHINESE = "chinese"
TEXT_SCRIPT_IDS = (SCRIPT_UNIVERSAL, SCRIPT_JAPANESE, SCRIPT_KOREAN, SCRIPT_CHINESE)

_LATIN_HINTS = (
    "segoe",
    "arial",
    "calibri",
    "cambria",
    "times new",
    "verdana",
    "tahoma",
    "helvetica",
    "roboto",
    "noto sans",
    "georgia",
    "trebuchet",
    "consolas",
    "franklin",
    "garamond",
    "constantia",
    "corbel",
    "bahnschrift",
    "lucida",
    "century gothic",
    "book antiqua",
    "palatino",
    "courier new",
    "comic sans",
    "impact",
    "gabriola",
)
_LATIN_PROBE = "ABCabc123"
_LATIN_FALLBACKS = [
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\calibri.ttf"),
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path(r"C:\Windows\Fonts\verdana.ttf"),
    Path(r"C:\Windows\Fonts\times.ttf"),
    Path(r"C:\Windows\Fonts\consola.ttf"),
]
_CJK_NAME_RE = re.compile(
    r"sim|hei|song|kai|fang|yuan|ming|gothic|mincho|meiryo|malgun|gulim|batang|dotum|"
    r"noto|source han|pingfang|hiragino|cjk|\bhan\b|han-|dengxian|fangsong|stkaiti",
    re.IGNORECASE,
)

_LEGACY_FALLBACKS = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansCJKsc-Regular.otf"),
    Path(r"C:\Windows\Fonts\malgun.ttf"),
    Path(r"C:\Windows\Fonts\malgunbd.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf"),
    Path(r"C:\Windows\Fonts\NotoSansCJKkr-Regular.otf"),
    Path(r"C:\Windows\Fonts\meiryo.ttc"),
    Path(r"C:\Windows\Fonts\YuGothM.ttc"),
    Path(r"/System/Library/Fonts/PingFang.ttc"),
    Path(r"/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
]


@dataclass(frozen=True)
class DiscoveredFont:
    display_name: str
    path: Path
    script_tags: Tuple[str, ...]
    score: int

    @property
    def label(self) -> str:
        tag_labels = {
            "latin": "LATIN",
            "sc": "SC",
            "tc": "TC",
            "jp": "JP",
            "kr": "KR",
            "cjk": "CJK",
        }
        if self.script_tags:
            tags = "/".join(tag_labels.get(tag, tag.upper()) for tag in self.script_tags)
        else:
            tags = "CJK"
        return f"{self.display_name} [{tags}]"


def _fonts_directory() -> Path:
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def _name_looks_cjk(name: str) -> bool:
    return bool(_CJK_NAME_RE.search(name))


def _name_looks_latin(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _LATIN_HINTS)


def _name_latin_tags(name: str) -> Tuple[str, ...]:
    return ("latin",) if _name_looks_latin(name) else ()


def _score_latin_font(name: str) -> int:
    lowered = name.lower()
    score = 0
    if "segoe ui" in lowered or lowered.startswith("segoe"):
        score += 120
    if "arial" in lowered:
        score += 110
    if "calibri" in lowered:
        score += 100
    if "tahoma" in lowered or "verdana" in lowered:
        score += 90
    if "times new roman" in lowered:
        score += 85
    if "consolas" in lowered:
        score += 70
    if "noto sans" in lowered and "cjk" not in lowered and "sc" not in lowered:
        score += 65
    if lowered.endswith("(truetype)"):
        score -= 5
    return score


def font_supports_latin(font_path: Path) -> bool:
    path = Path(font_path)
    if not path.exists():
        return False
    return all(font_has_glyph(path, char) for char in _LATIN_PROBE)


def _name_tags(name: str) -> Tuple[str, ...]:
    lowered = name.lower()
    tags: List[str] = []
    if any(hint in lowered for hint in _SC_HINTS):
        tags.append("sc")
    if any(hint in lowered for hint in _TC_HINTS):
        tags.append("tc")
    if any(hint in lowered for hint in _JP_HINTS):
        tags.append("jp")
    if any(hint in lowered for hint in _KR_HINTS):
        tags.append("kr")
    if not tags and any(hint in lowered for hint in ("cjk", "han", "pingfang", "source han")):
        tags.append("cjk")
    return tuple(tags)


def _score_font(name: str, tags: Tuple[str, ...]) -> int:
    lowered = name.lower()
    score = 0
    if "sc" in tags:
        score += 120
    if "tc" in tags:
        score += 80
    if "jp" in tags:
        score += 60
    if "kr" in tags:
        score += 40
    if "cjk" in tags:
        score += 50
    if "yahei" in lowered or "microsoft yahei" in lowered:
        score += 40
    if "simhei" in lowered:
        score += 35
    if "noto sans sc" in lowered or "noto sans cjk sc" in lowered:
        score += 30
    if "simsun" in lowered:
        score += 20
    if lowered.endswith("(truetype)"):
        score -= 5
    return score


def _registry_font_entries() -> Dict[str, Path]:
    entries: Dict[str, Path] = {}
    try:
        import winreg
    except ImportError:
        return entries

    fonts_dir = _fonts_directory()
    try:
        try:
            from defender_audit import log_registry_read

            log_registry_read(
                r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
                purpose="font enumeration",
            )
        except Exception:
            pass
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
        ) as key:
            index = 0
            while True:
                try:
                    display_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                path = Path(str(value))
                if not path.is_absolute():
                    path = fonts_dir / path
                if path.suffix.lower() not in _FONT_EXTS:
                    continue
                if path.exists():
                    entries[display_name] = path.resolve()
    except OSError:
        pass
    return entries


def _glob_font_files() -> Dict[str, Path]:
    fonts_dir = _fonts_directory()
    if not fonts_dir.exists():
        return {}
    found: Dict[str, Path] = {}
    for path in fonts_dir.iterdir():
        if path.suffix.lower() not in _FONT_EXTS:
            continue
        if path.is_file():
            found[path.stem] = path.resolve()
    return found


def discover_cjk_fonts(deep_scan: bool = False) -> Tuple[DiscoveredFont, ...]:
    """Return installed fonts likely to support CJK, best matches first."""
    by_path: Dict[Path, DiscoveredFont] = {}
    entries = {**_glob_font_files(), **_registry_font_entries()}
    for display_name, path in entries.items():
        path = path.resolve()
        if path.suffix.lower() not in _FONT_EXTS:
            continue
        tags = _name_tags(display_name)
        if not tags and not _name_looks_cjk(display_name):
            if path.stem.lower() not in {p.stem.lower() for p in _LEGACY_FALLBACKS}:
                continue
            tags = ("cjk",)
        score = _score_font(display_name, tags)
        existing = by_path.get(path)
        if existing is None or score > existing.score:
            by_path[path] = DiscoveredFont(
                display_name=display_name.replace("(TrueType)", "").strip(),
                path=path,
                script_tags=tags,
                score=score,
            )

    for fallback in _LEGACY_FALLBACKS:
        if not fallback.exists():
            continue
        path = fallback.resolve()
        if path in by_path:
            continue
        name = path.stem
        tags = _name_tags(name)
        by_path[path] = DiscoveredFont(
            display_name=name,
            path=path,
            script_tags=tags or ("cjk",),
            score=_score_font(name, tags or ("cjk",)),
        )

    if deep_scan:
        for display_name, path in entries.items():
            path = Path(path).resolve()
            if path in by_path or path.suffix.lower() not in _FONT_EXTS:
                continue
            tags_probe = _name_tags(display_name) or ("cjk",)
            require_hangul = "kr" in tags_probe
            if not path.exists() or not font_supports_sample(path, require_hangul=require_hangul):
                continue
            tags = _name_tags(display_name) or ("cjk",)
            by_path[path] = DiscoveredFont(
                display_name=display_name.replace("(TrueType)", "").strip(),
                path=path,
                script_tags=tags,
                score=_score_font(display_name, tags) + 5,
            )

    return tuple(sorted(by_path.values(), key=lambda item: (-item.score, item.display_name.lower())))


def discover_latin_fonts(deep_scan: bool = False) -> Tuple[DiscoveredFont, ...]:
    """Return installed fonts suitable for Latin / universal text."""
    by_path: Dict[Path, DiscoveredFont] = {}
    entries = {**_glob_font_files(), **_registry_font_entries()}
    for display_name, path in entries.items():
        path = Path(path).resolve()
        if path.suffix.lower() not in _FONT_EXTS:
            continue
        if not _name_looks_latin(display_name) and path.stem.lower() not in {p.stem.lower() for p in _LATIN_FALLBACKS}:
            continue
        if _name_looks_cjk(display_name) and not _name_looks_latin(display_name):
            continue
        score = _score_latin_font(display_name)
        existing = by_path.get(path)
        if existing is None or score > existing.score:
            by_path[path] = DiscoveredFont(
                display_name=display_name.replace("(TrueType)", "").strip(),
                path=path,
                script_tags=("latin",),
                score=score,
            )

    for fallback in _LATIN_FALLBACKS:
        if not fallback.exists():
            continue
        path = fallback.resolve()
        if path in by_path:
            continue
        name = path.stem
        by_path[path] = DiscoveredFont(
            display_name=name,
            path=path,
            script_tags=("latin",),
            score=_score_latin_font(name),
        )

    if deep_scan:
        for display_name, path in entries.items():
            path = Path(path).resolve()
            if path in by_path or path.suffix.lower() not in _FONT_EXTS or not path.exists():
                continue
            if _name_looks_cjk(display_name) and not _name_looks_latin(display_name):
                continue
            if not font_supports_latin(path):
                continue
            by_path[path] = DiscoveredFont(
                display_name=display_name.replace("(TrueType)", "").strip(),
                path=path,
                script_tags=("latin",),
                score=_score_latin_font(display_name) + 5,
            )

    return tuple(sorted(by_path.values(), key=lambda item: (-item.score, item.display_name.lower())))


def font_matches_script(font: DiscoveredFont, script: str) -> bool:
    tags = font.script_tags
    if script == SCRIPT_UNIVERSAL:
        return "latin" in tags
    if script == SCRIPT_JAPANESE:
        return "jp" in tags or "cjk" in tags
    if script == SCRIPT_KOREAN:
        return "kr" in tags
    if script == SCRIPT_CHINESE:
        return "sc" in tags or "tc" in tags or "cjk" in tags
    return True


def filter_fonts_for_script(fonts: Sequence[DiscoveredFont], script: str) -> Tuple[DiscoveredFont, ...]:
    return tuple(font for font in fonts if font_matches_script(font, script))


def filter_font_labels(
    fonts: Sequence[DiscoveredFont],
    search_query: str = "",
) -> Tuple[DiscoveredFont, ...]:
    query = (search_query or "").strip().lower()
    if not query:
        return tuple(fonts)
    tokens = [part for part in re.split(r"\s+", query) if part]
    matched: List[DiscoveredFont] = []
    for font in fonts:
        haystack = f"{font.display_name} {font.label}".lower()
        if all(token in haystack for token in tokens):
            matched.append(font)
    return tuple(matched)


def discover_fonts_for_script(script: str, deep_scan: bool = False) -> Tuple[DiscoveredFont, ...]:
    if script == SCRIPT_UNIVERSAL:
        return discover_latin_fonts(deep_scan=deep_scan)
    return filter_fonts_for_script(discover_cjk_fonts(deep_scan=deep_scan), script)


def _font_covers_text(font: DiscoveredFont, text: str) -> bool:
    if not text.strip():
        return True
    missing = missing_glyphs(text, font.path)
    return not missing


def _score_font_for_text(font: DiscoveredFont, text: str) -> int:
    score = font.score
    scripts = text_scripts(text)
    if "kr" in scripts:
        if "kr" in font.script_tags:
            score += 200
        elif "cjk" in font.script_tags:
            score += 30
        else:
            score -= 80
    if "jp" in scripts and "jp" in font.script_tags:
        score += 80
    if "sc" in scripts and "sc" in font.script_tags:
        score += 40
    if text.strip() and _font_covers_text(font, text):
        score += 100
    return score


def find_font_for_text(
    text: str = "",
    preferred: Path | None = None,
    script: str | None = None,
) -> Path:
    """Pick a font that matches the scripts in *text* (Hangul → Korean faces first)."""
    if preferred is not None:
        path = Path(preferred)
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"Font not found: {path}")

    if script:
        fonts = discover_fonts_for_script(script)
    else:
        fonts = discover_cjk_fonts()
    if text.strip() and fonts:
        ranked = sorted(fonts, key=lambda item: (-_score_font_for_text(item, text), item.display_name.lower()))
        for font in ranked:
            if _font_covers_text(font, text):
                return font.path
        return ranked[0].path

    return find_cjk_font()


def find_cjk_font(preferred: Path | None = None) -> Path:
    """Resolve the best font path for Mandarin-first text rendering."""
    return find_font_for_text("", preferred=preferred)


def resolve_font_path(selection: str | None = None, browse_path: Path | None = None) -> Path:
    if browse_path is not None:
        path = Path(browse_path)
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"Font not found: {path}")

    selection = (selection or "").strip()
    if not selection:
        return find_cjk_font()

    for font in discover_cjk_fonts():
        if font.label == selection or font.display_name == selection:
            return font.path

    path = Path(selection)
    if path.exists():
        return path.resolve()

    return find_cjk_font()


def _load_truetype(path: Path, size: int, bold: bool = False):
    from PIL import ImageFont

    path = Path(path)
    if path.suffix.lower() == ".ttc" and bold:
        for index in (1, 0):
            try:
                return ImageFont.truetype(str(path), size, index=index)
            except OSError:
                continue
    return ImageFont.truetype(str(path), size)


def font_has_glyph(font_path: Path, char: str, size: int = _PROBE_SIZE) -> bool:
    if len(char) != 1:
        return False
    try:
        font = _load_truetype(Path(font_path), size)
    except OSError:
        return False

    if hasattr(font, "has_glyph"):
        try:
            return bool(font.has_glyph(char))
        except Exception:
            pass

    try:
        from PIL import Image, ImageDraw

        draw = ImageDraw.Draw(Image.new("L", (max(size * 2, 8), max(size * 2, 8)), 0))
        bbox = draw.textbbox((0, 0), char, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width > 1 and height > 1:
            return True
    except Exception:
        pass

    mask = font.getmask(char)
    return mask.size[0] > 1 and mask.size[1] > 1


def font_supports_sample(font_path: Path, require_hangul: bool = False) -> bool:
    path = Path(font_path)
    if not path.exists():
        return False
    hits = sum(1 for char in _PROBE_CHARS if font_has_glyph(path, char))
    if hits < 2:
        return False
    if require_hangul:
        return font_has_glyph(path, "가") and font_has_glyph(path, "한")
    return True


def missing_glyphs(text: str, font_path: Path) -> List[str]:
    missing: List[str] = []
    for char in unique_chars(text):
        if not is_cjk_char(char):
            continue
        if not font_has_glyph(font_path, char):
            missing.append(char)
    return missing


def validate_text_coverage(text: str, font_path: Path) -> Tuple[bool, List[str]]:
    missing = missing_glyphs(text, font_path)
    return (not missing, missing)


def coverage_message_key(text: str, ok: bool, missing: Sequence[str]) -> str:
    if ok:
        if text_contains_hangul(text):
            return "text_coverage_ok_korean"
        return "text_coverage_ok"
    if text_contains_hangul(text):
        return "text_coverage_missing_korean"
    return "text_coverage_missing"


def recommend_font_label_for_text(text: str, script: str | None = None) -> str | None:
    if not text_contains_hangul(text):
        return None
    fonts = discover_fonts_for_script(script or SCRIPT_KOREAN) if script else discover_cjk_fonts()
    for font in fonts:
        if "kr" in font.script_tags and _font_covers_text(font, text):
            return font.label
    for font in fonts:
        if "kr" in font.script_tags:
            return font.label
    return None


def format_missing_chars(chars: Sequence[str], limit: int = 12) -> str:
    if not chars:
        return ""
    shown = "".join(chars[:limit])
    if len(chars) > limit:
        shown += f" (+{len(chars) - limit} more)"
    return shown
