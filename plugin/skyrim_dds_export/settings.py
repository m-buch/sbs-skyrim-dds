"""QSettings plugin settings and skydds.exe discovery."""

import hashlib
import json
import os
import shutil

from . import presets
from .qt import QtCore


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

    def _stored_list(self, key):
        raw = self._store.value(key, "")
        if not raw:
            return []
        try:
            stored = json.loads(raw)
        except ValueError:
            return []
        return stored if isinstance(stored, list) else []

    @property
    def default_presets(self):
        edits = {preset.get("name"): preset for preset in self._stored_list("default_presets")}
        merged = []
        for preset in presets.default_presets():
            merged.append(edits.get(preset["name"], preset))
        return presets.normalize_all(merged)

    @default_presets.setter
    def default_presets(self, value):
        self._store.setValue("default_presets", json.dumps(presets.normalize_all(value)))
        self._store.sync()

    def reset_default_presets(self):
        self._store.remove("default_presets")
        self._store.sync()

    @property
    def user_presets(self):
        return presets.normalize_all(self._stored_list("user_presets"))

    @user_presets.setter
    def user_presets(self, value):
        self._store.setValue("user_presets", json.dumps(presets.normalize_all(value)))
        self._store.sync()

    def all_presets(self):
        return presets.normalize_all(self.default_presets + self.user_presets)

    @staticmethod
    def _graph_key(graph_id):
        digest = hashlib.md5(graph_id.encode("utf-8")).hexdigest()
        return "graphs/" + digest

    def graph_state(self, graph_id):
        """Stored dialog state for a graph."""
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
