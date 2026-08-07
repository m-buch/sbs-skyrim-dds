"""Tests for the plugin's slot table helpers.
"""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SLOTS_PY = REPO / "plugin" / "skyrim_dds_export" / "slots.py"


def load_slots():
    spec = importlib.util.spec_from_file_location("plugin_slots", SLOTS_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


slots = load_slots()


def test_slot_names_cover_the_ck_slots():
    names = slots.slot_names()
    for expected in ("diffuse", "normal", "glow", "parallax", "envmask"):
        assert expected in names


def test_default_suffixes_match_skyrim_conventions():
    defaults = slots.default_suffixes()
    assert defaults["diffuse"] == ""
    assert defaults["normal"] == "_n"
    assert defaults["glow"] == "_g"
    assert defaults["parallax"] == "_p"
    assert defaults["envmask"] == "_m"


def test_every_slot_has_a_default_suffix():
    defaults = slots.default_suffixes()
    assert set(defaults) == set(slots.slot_names())


def test_suffixes_are_unique_apart_from_diffuse():
    defaults = slots.default_suffixes()
    used = [suffix for suffix in defaults.values() if suffix]
    assert len(used) == len(set(used)), "two slots share a suffix; filenames would collide"
