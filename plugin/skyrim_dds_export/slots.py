"""Slot table lookups."""

import json
import os


def _slots_data():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slots.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["slots"]


def slot_names():
    return list(_slots_data().keys())


def default_suffixes():
    """{slot: default suffix} from slots.json."""
    defaults = {}
    for slot, info in _slots_data().items():
        suffixes = info["suffixes"]
        defaults[slot] = suffixes[0] if suffixes else ""
    return defaults
