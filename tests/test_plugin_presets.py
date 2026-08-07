"""Tests for the plugin's preset table."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRESETS_PY = REPO / "plugin" / "skyrim_dds_export" / "presets.py"


def load():
    spec = importlib.util.spec_from_file_location("plugin_presets", PRESETS_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


presets = load()


def test_defaults_cover_the_ck_slots():
    names = [preset["name"] for preset in presets.default_presets()]
    for expected in ("diffuse", "normal", "glow", "parallax", "envmask"):
        assert expected in names


def test_defaults_are_valid_and_match_conventions():
    by_name = {preset["name"]: preset for preset in presets.default_presets()}
    assert by_name["diffuse"]["suffix"] == ""
    assert by_name["normal"]["suffix"] == "_n"
    assert by_name["normal"]["format"] == "bc7"
    assert by_name["normal"]["alpha"] == "encoded"
    assert by_name["normal"]["colorspace"] == "linear"
    assert by_name["diffuse"]["colorspace"] == "srgb"
    for preset in by_name.values():
        assert preset["format"] in presets.FORMATS
        assert preset["colorspace"] in presets.COLORSPACES
        assert preset["alpha"] in presets.ALPHA_KINDS


def test_default_suffixes_are_unique():
    used = [p["suffix"] for p in presets.default_presets() if p["suffix"]]
    assert len(used) == len(set(used))


def test_normalize_fills_missing_fields():
    result = presets.normalize({"name": "custom"})
    assert result["name"] == "custom"
    assert result["suffix"] == ""
    assert result["format"] in presets.FORMATS
    assert result["colorspace"] in presets.COLORSPACES
    assert result["alpha"] in presets.ALPHA_KINDS


def test_normalize_replaces_invalid_values():
    result = presets.normalize(
        {"name": "x", "format": "astc", "colorspace": "cmyk", "alpha": "maybe"}
    )
    assert result["format"] in presets.FORMATS
    assert result["colorspace"] in presets.COLORSPACES
    assert result["alpha"] in presets.ALPHA_KINDS


def test_normalize_all_drops_unnamed_and_duplicate_presets():
    result = presets.normalize_all(
        [
            {"name": "a", "format": "bc1"},
            {"name": "", "format": "bc7"},
            {"name": "  ", "format": "bc7"},
            {"name": "a", "format": "bc7"},
            {"name": "b", "format": "bc4"},
        ]
    )
    assert [preset["name"] for preset in result] == ["a", "b"]
    assert result[0]["format"] == "bc1"  # first wins


def test_custom_preset_survives_round_trip():
    custom = {
        "name": "basecolor",
        "suffix": "_basecolor",
        "format": "bc7",
        "colorspace": "srgb",
        "alpha": "none",
    }
    result = presets.normalize_all(presets.default_presets() + [custom])
    assert presets.find(result, "basecolor") == custom


def test_find_returns_none_for_unknown():
    assert presets.find(presets.default_presets(), "nope") is None
