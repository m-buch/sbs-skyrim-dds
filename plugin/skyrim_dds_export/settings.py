"""QSettings plugin settings and skydds.exe discovery."""

import hashlib
import json
import os
import shutil

from .qt import QtCore

ALPHA_MODES = ["auto", "none", "blend", "test"]


def bundled_skydds():
    """skydds.exe shipped inside the plugin folder, if present."""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(plugin_dir, "skydds.exe"),
        os.path.join(plugin_dir, "bin", "skydds.exe"),
    ):
        if os.path.isfile(candidate):
            return candidate
    return ""


def resolve_skydds(configured=""):
    if configured and os.path.isfile(configured):
        return configured
    return bundled_skydds() or shutil.which("skydds") or ""


class Settings:
    def __init__(self):
        self._store = QtCore.QSettings("sbsdesigner-skyrim-dds", "skyrim_dds_export")

    @property
    def skydds_path(self):
        """Explicit override; usually empty since the release bundles the exe."""
        return self._store.value("skydds_path", "")

    @skydds_path.setter
    def skydds_path(self, value):
        self._store.setValue("skydds_path", value)

    def resolved_skydds(self):
        return resolve_skydds(self.skydds_path)

    @property
    def suffix_overrides(self):
        """Global {slot: suffix} overrides. Slots absent here use slots.json."""
        raw = self._store.value("suffix_overrides", "")
        if not raw:
            return {}
        try:
            overrides = json.loads(raw)
        except ValueError:
            return {}
        return overrides if isinstance(overrides, dict) else {}

    @suffix_overrides.setter
    def suffix_overrides(self, overrides):
        self._store.setValue("suffix_overrides", json.dumps(overrides))
        self._store.sync()

    def suffix_for(self, slot, defaults):
        """Suffix for a slot: the global override if set, else the default.
        An override of "" is meaningful (diffuse has no suffix by default)."""
        overrides = self.suffix_overrides
        if slot in overrides:
            return overrides[slot]
        return defaults.get(slot, "")

    @staticmethod
    def _graph_key(graph_id):
        digest = hashlib.md5(graph_id.encode("utf-8")).hexdigest()
        return "graphs/" + digest

    def graph_state(self, graph_id):
        """Stored dialog state for a graph: output_dir, filename, alpha_mode,
        outputs {name: {enabled, slot}}. Empty dict if never exported."""
        raw = self._store.value(self._graph_key(graph_id), "")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            return {}

    def set_graph_state(self, graph_id, state):
        stored = dict(state, graph=graph_id)
        self._store.setValue(self._graph_key(graph_id), json.dumps(stored))
        self._store.sync()
