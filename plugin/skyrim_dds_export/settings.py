"""QSettings plugin settings.
"""

import hashlib
import json

from .qt import QtCore, QtWidgets

ALPHA_MODES = ["auto", "none", "blend", "test"]


class Settings:
    def __init__(self):
        self._store = QtCore.QSettings("sbsdesigner-skyrim-dds", "skyrim_dds_export")

    @property
    def skydds_path(self):
        return self._store.value("skydds_path", "")

    @skydds_path.setter
    def skydds_path(self, value):
        self._store.setValue("skydds_path", value)

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
        self._store.setValue(self._graph_key(graph_id), json.dumps(state))


class SettingsDialog(QtWidgets.QDialog):
    """Global settings"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Skyrim DDS Export Settings")
        self.setMinimumWidth(480)

        self._skydds_edit = QtWidgets.QLineEdit(settings.skydds_path)
        browse = QtWidgets.QPushButton("...")
        browse.clicked.connect(self._browse)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self._skydds_edit)
        row.addWidget(browse)

        form = QtWidgets.QFormLayout()
        form.addRow("skydds.exe:", row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Locate skydds.exe", self._skydds_edit.text(), "Executables (*.exe)"
        )
        if path:
            self._skydds_edit.setText(path)

    def accept(self):
        self._settings.skydds_path = self._skydds_edit.text().strip()
        super().accept()
