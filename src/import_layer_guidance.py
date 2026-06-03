"""User-facing hints for FH vinyl import layer counts and table safety checks."""

from __future__ import annotations

from security_policy import MAX_TEMPLATE_LAYER_COUNT

FH_BOUNDARY_LAYERS = 4


def strict_required_for_template(template_layers: int) -> int:
    required = min(int(template_layers), MAX_TEMPLATE_LAYER_COUNT)
    return min(required, max(32, required // 4))


def recommended_template_count(json_drawable: int) -> int:
    return min(int(json_drawable) + FH_BOUNDARY_LAYERS, MAX_TEMPLATE_LAYER_COUNT)


def template_layers_to_add(json_drawable: int, template_layers: int) -> int:
    return max(0, recommended_template_count(json_drawable) - int(template_layers))


def format_capacity_hint(json_drawable: int, template_layers: int) -> str | None:
    if json_drawable <= 0:
        return None
    template_layers = int(template_layers)
    add = template_layers_to_add(json_drawable, template_layers)
    if add <= 0:
        if json_drawable > max(0, template_layers - FH_BOUNDARY_LAYERS):
            return (
                f"JSON has {json_drawable} drawable layers at the game maximum ({MAX_TEMPLATE_LAYER_COUNT}). "
                f"Import will keep {max(0, template_layers - FH_BOUNDARY_LAYERS)} drawable layers "
                f"and reserve {FH_BOUNDARY_LAYERS} boundary layers."
            )
        return None
    target = recommended_template_count(json_drawable)
    return (
        f"JSON has {json_drawable} drawable layers; FH reserves {FH_BOUNDARY_LAYERS} boundary layers. "
        f"Add at least {add} layer(s) in-game (recommended template count: {target})."
    )


def looks_like_stale_table(strict_valid: int, strict_required: int) -> bool:
    return strict_valid < min(32, max(1, strict_required // 10))


def format_safety_failure_lines(
    *,
    template_layers: int,
    strict_valid: int,
    strict_required: int,
    scanned: int,
    loose_valid: int = 0,
) -> list[str]:
    lines = [
        (
            f"Layer table safety check failed: found {strict_valid}/{strict_required} "
            f"required initialized layer slots (scanned {scanned} table indices; "
            f"{loose_valid} loose-valid pointers). Import aborted."
        ),
    ]
    if looks_like_stale_table(strict_valid, strict_required):
        lines.append(
            "This usually means a stale layer-table address or wrong game menu state — "
            "not that your template is too small."
        )
        lines.append(
            "Fix: stay in Vinyl Group Editor with an ungrouped template, confirm the layer count "
            "matches exactly, restart FH if needed, then import again so the app re-locates memory."
        )
    else:
        lines.append(
            "Many template slots look empty or cleared in memory (zero scale / invalid layer data)."
        )
        lines.append(
            f"Try a fresh blank template with at least {template_layers} layers, "
            "or reload the vinyl group before importing."
        )
    return lines
