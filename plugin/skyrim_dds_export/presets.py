"""Export presets"""

import json
import os

FORMATS = ["bc1", "bc1a", "bc4", "bc7"]
COLORSPACES = ["srgb", "linear"]
ALPHA_KINDS = ["none", "test", "blend", "encoded"]

FIELDS = ("name", "suffix", "format", "colorspace", "alpha")


def default_presets():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slots.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["presets"]


def normalize(preset):
    """Fills in missing/invalid fields so a stored preset is always usable."""
    result = {field: str(preset.get(field, "")) for field in FIELDS}
    if result["format"] not in FORMATS:
        result["format"] = "bc7"
    if result["colorspace"] not in COLORSPACES:
        result["colorspace"] = "linear"
    if result["alpha"] not in ALPHA_KINDS:
        result["alpha"] = "none"
    return result


def normalize_all(presets):
    """Normalizes a preset list and drops entries without a name."""
    seen = set()
    result = []
    for preset in presets:
        normalized = normalize(preset)
        name = normalized["name"].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized["name"] = name
        result.append(normalized)
    return result


def find(presets, name):
    for preset in presets:
        if preset["name"] == name:
            return preset
    return None
