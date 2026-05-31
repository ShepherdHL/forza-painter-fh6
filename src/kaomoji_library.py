"""Curated kaomoji (Japanese emoticon) strings for the Text vinyl picker."""

from __future__ import annotations

import functools
from typing import List, Tuple

# Popular faces chosen for relatively common Unicode coverage (ASCII + CJK punctuation).
# Complex site-only kaomoji may still need Trace from image.
_KAOMOJI: Tuple[str, ...] = (
    "(◕‿◕)",
    "(｡◕‿◕｡)",
    "(◕‿◕)✿",
    "(*^‿^*)",
    "(^人^)",
    "(^_^)",
    "(^ω^)",
    "(´･ω･`)",
    "(・∀・)",
    "(￣▽￣)",
    "(￣ω￣)",
    "(＾▽＾)",
    "(≧▽≦)",
    "(｀・ω・´)",
    "(；一_一)",
    "(>_<)",
    "(T_T)",
    "(╥_╥)",
    "(ಥ﹏ಥ)",
    "(ノ_<)",
    "¯\\_(ツ)_/¯",
    "(╯°□°）╯︵ ┻━┻",
    "┬─┬ノ( º _ ºノ)",
    "(╯°□°)╯︵ ┻━┻",
    "(ノ°益°)ノ彡┻━┻",
    "ヽ(≧▽≦)ノ",
    "ヾ(≧▽≦*)o",
    "ヽ(・∀・)ﾉ",
    "(ノ^_^)ノ",
    "(づ｡◕‿‿◕｡)づ",
    "(づ￣ ³￣)づ",
    "( ˘▽˘)っ♨",
    "ψ(｀∇´)ψ",
    "(ง •̀_•́)ง",
    "(•̀o•́)ง",
    "♪(´ε｀ )",
    "( ˇ෴ˇ )",
    "ʕ•ᴥ•ʔ",
    "(✿◠‿◠)",
    "(◠‿◠)",
    "(●´ω｀●)",
    "(´∀｀)♡",
    "( ˶°ㅁ°) !!",
    "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
    "(☞ﾟ∀ﾟ)☞",
    "(☜ﾟ∀ﾟ)☜",
    "( ͡° ͜ʖ ͡°)",
    "( ͡~ ͜ʖ ͡~)",
    "┐(´д`)┌",
    "┐(´∀｀)┌",
    "╮(╯_╰)╭",
    "(；☉_☉)",
    "(⊙_⊙)",
    "(°ロ°)",
    "(´･_･`)",
    "(´-ω-`)",
    "(´；ω；`)",
    "(；ω；)",
    "(´；д；`)",
    "(｡･ω･｡)ﾉ♡",
    "( ･ิω･ิ)",
    "(๑•̀ㅂ•́)و✧",
    "(๑>◡<๑)",
    "(๑˃̵ᴗ˂̵)",
    "٩(◕‿◕)۶",
    "(づ ◕‿◕ )づ",
    "(っ◕‿◕)っ",
    "(っ´ω`)っ",
    "（・∀・）",
    "（＾＾）",
    "（；´д｀）",
    "（´・ω・｀）",
)

PAGE_SIZE = 24
GRID_COLUMNS = 8


@functools.lru_cache(maxsize=1)
def kaomoji_library() -> Tuple[str, ...]:
    return _KAOMOJI


def library_total() -> int:
    return len(kaomoji_library())


def filter_kaomoji(query: str) -> List[str]:
    library = kaomoji_library()
    query = (query or "").strip()
    if not query:
        return list(library)
    lowered = query.lower()
    return [item for item in library if lowered in item.lower() or query in item]


def paginate_kaomoji(
    items: List[str],
    page: int,
    *,
    page_size: int = PAGE_SIZE,
) -> Tuple[List[str], int, int]:
    if not items:
        return [], 0, 1
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start : start + page_size], page, total_pages
