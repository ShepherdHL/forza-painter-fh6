import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

spec = importlib.util.spec_from_file_location(
    "import_layer_guidance",
    SRC / "import_layer_guidance.py",
)
guidance = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guidance)


def test_strict_required_for_1800():
    assert guidance.strict_required_for_template(1800) == 450


def test_template_layers_to_add_for_1800_json():
    assert guidance.template_layers_to_add(1800, 1800) == 4
    assert guidance.recommended_template_count(1800) == 1804


def test_template_layers_to_add_at_game_max():
    assert guidance.template_layers_to_add(3000, 3000) == 0


def test_capacity_hint_requests_four_more_layers():
    hint = guidance.format_capacity_hint(1800, 1800)
    assert hint is not None
    assert "Add at least 4" in hint
    assert "1804" in hint


def test_safety_failure_stale_table_wording():
    lines = guidance.format_safety_failure_lines(
        template_layers=1800,
        strict_valid=5,
        strict_required=450,
        scanned=1800,
        loose_valid=12,
    )
    joined = "\n".join(lines)
    assert "5/450" in joined
    assert "stale" in joined.lower()
    assert guidance.looks_like_stale_table(5, 450)


def test_safety_failure_sparse_template_wording():
    lines = guidance.format_safety_failure_lines(
        template_layers=1800,
        strict_valid=200,
        strict_required=450,
        scanned=1800,
        loose_valid=1800,
    )
    joined = "\n".join(lines)
    assert "blank template" in joined.lower()
    assert not guidance.looks_like_stale_table(200, 450)
