"""Per-graph export dialog: an Export tab and a Settings tab."""

import os

from . import exporter
from .qt import QtWidgets
from .settings import ALPHA_MODES, bundled_skydds, resolve_skydds

UNASSIGNED = "(unassigned)"


class _OutputRow:
    def __init__(self, output, checkbox, slot_combo, preview):
        self.output = output
        self.checkbox = checkbox
        self.slot_combo = slot_combo
        self.preview = preview


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, graph_name, outputs, state, settings, parent=None):
        """outputs: list of exporter.GraphOutput. state: stored per-graph dict."""
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Skyrim DDS Export — " + graph_name)
        self.setMinimumWidth(580)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_export_tab(graph_name, outputs, state), "Export")
        tabs.addTab(self._build_settings_tab(), "Settings")

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Export")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self._update_previews()

    def _build_export_tab(self, graph_name, outputs, state):
        tab = QtWidgets.QWidget()

        self._dir_edit = QtWidgets.QLineEdit(state.get("output_dir", ""))
        browse = QtWidgets.QPushButton("...")
        browse.clicked.connect(self._browse_dir)
        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(self._dir_edit)
        dir_row.addWidget(browse)

        self._name_edit = QtWidgets.QLineEdit(state.get("filename", "") or graph_name)
        self._name_edit.textChanged.connect(self._update_previews)

        self._alpha_combo = QtWidgets.QComboBox()
        self._alpha_combo.addItems(ALPHA_MODES)
        alpha = state.get("alpha_mode", "auto")
        self._alpha_combo.setCurrentText(alpha if alpha in ALPHA_MODES else "auto")
        self._alpha_combo.setToolTip(
            "How the diffuse slot treats alpha. blend keeps full RGB (BC7); test is 1-bit (BC1a)."
        )

        form = QtWidgets.QFormLayout()
        form.addRow("Output directory:", dir_row)
        form.addRow("Base filename:", self._name_edit)
        form.addRow("Diffuse alpha mode:", self._alpha_combo)

        outputs_box = QtWidgets.QGroupBox("Outputs")
        grid = QtWidgets.QGridLayout(outputs_box)
        grid.setColumnStretch(2, 1)
        slots = exporter.slot_names()
        stored_outputs = state.get("outputs", {})
        self._rows = []
        for row_index, output in enumerate(outputs):
            stored = stored_outputs.get(output.name, {})

            checkbox = QtWidgets.QCheckBox(output.name)
            checkbox.setChecked(stored.get("enabled", False))
            checkbox.toggled.connect(self._update_previews)

            slot_combo = QtWidgets.QComboBox()
            slot_combo.addItem(UNASSIGNED)
            slot_combo.addItems(slots)
            slot = stored.get("slot")
            if slot in slots:
                slot_combo.setCurrentText(slot)
            slot_combo.currentTextChanged.connect(self._update_previews)

            preview = QtWidgets.QLabel()
            grid.addWidget(checkbox, row_index, 0)
            grid.addWidget(slot_combo, row_index, 1)
            grid.addWidget(preview, row_index, 2)
            self._rows.append(_OutputRow(output, checkbox, slot_combo, preview))

        layout = QtWidgets.QVBoxLayout(tab)
        layout.addLayout(form)
        layout.addWidget(outputs_box)
        layout.addStretch(1)
        return tab

    def _build_settings_tab(self):
        tab = QtWidgets.QWidget()

        self._skydds_edit = QtWidgets.QLineEdit(self._settings.skydds_path)
        bundled = bundled_skydds()
        self._skydds_edit.setPlaceholderText(
            "auto: " + bundled if bundled else "not found — browse to skydds.exe"
        )
        self._skydds_edit.textChanged.connect(self._update_skydds_status)
        browse = QtWidgets.QPushButton("...")
        browse.clicked.connect(self._browse_skydds)
        clear = QtWidgets.QPushButton("Use bundled")
        clear.setToolTip("Clear the override and use the skydds.exe shipped with the plugin")
        clear.clicked.connect(lambda: self._skydds_edit.setText(""))
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self._skydds_edit)
        row.addWidget(browse)
        row.addWidget(clear)

        self._skydds_status = QtWidgets.QLabel()
        self._skydds_status.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.addRow("skydds.exe override:", row)
        form.addRow("", self._skydds_status)

        layout = QtWidgets.QVBoxLayout(tab)
        layout.addLayout(form)
        layout.addStretch(1)
        self._update_skydds_status()
        return tab

    def _update_skydds_status(self):
        resolved = resolve_skydds(self._skydds_edit.text().strip())
        if resolved:
            self._skydds_status.setText("Using: " + resolved)
        else:
            self._skydds_status.setText(
                "No skydds.exe found. Place it next to the plugin, put it on PATH, "
                "or browse to it above."
            )

    def _browse_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Output directory (e.g. Data/textures/<mod>)", self._dir_edit.text()
        )
        if path:
            self._dir_edit.setText(path)

    def _browse_skydds(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Locate skydds.exe", self._skydds_edit.text(), "Executables (*.exe)"
        )
        if path:
            self._skydds_edit.setText(path)

    def _file_name(self, row):
        slot = row.slot_combo.currentText()
        if slot == UNASSIGNED:
            return None
        return self._name_edit.text().strip() + exporter.canonical_suffix(slot) + ".dds"

    def _update_previews(self):
        for row in self._rows:
            if not row.checkbox.isChecked():
                row.preview.setText("")
                continue
            name = self._file_name(row)
            row.preview.setText("→ " + name if name else "no slot assigned")

    def _warn(self, message):
        QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", message)

    def accept(self):
        self._settings.skydds_path = self._skydds_edit.text().strip()

        if not self._dir_edit.text().strip():
            self._warn("Choose an output directory.")
            return
        if not self._name_edit.text().strip():
            self._warn("Choose a base filename.")
            return
        checked = [row for row in self._rows if row.checkbox.isChecked()]
        if not checked:
            self._warn("No outputs selected.")
            return
        unassigned = [
            row.output.name for row in checked if row.slot_combo.currentText() == UNASSIGNED
        ]
        if unassigned:
            self._warn("These outputs have no slot assigned:\n\n" + "\n".join(unassigned))
            return

        names = [self._file_name(row) for row in checked]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            self._warn(
                "Two or more outputs would write the same file:\n\n"
                + "\n".join(duplicates)
                + "\n\nGive them different slots."
            )
            return
        if not resolve_skydds(self._skydds_edit.text().strip()):
            self._warn("No skydds.exe found — set it on the Settings tab.")
            return
        super().accept()

    def export_items(self):
        return [
            exporter.ExportItem(row.output, row.slot_combo.currentText(), self._file_name(row))
            for row in self._rows
            if row.checkbox.isChecked()
        ]

    def state(self):
        """Dialog state to persist for this graph."""
        outputs = {}
        for row in self._rows:
            slot = row.slot_combo.currentText()
            outputs[row.output.name] = {
                "enabled": row.checkbox.isChecked(),
                "slot": "" if slot == UNASSIGNED else slot,
            }
        return {
            "output_dir": self._dir_edit.text().strip(),
            "filename": self._name_edit.text().strip(),
            "alpha_mode": self._alpha_combo.currentText(),
            "outputs": outputs,
        }

    @property
    def output_dir(self):
        return os.path.normpath(self._dir_edit.text().strip())

    @property
    def alpha_mode(self):
        return self._alpha_combo.currentText()

    @property
    def skydds_path(self):
        return resolve_skydds(self._skydds_edit.text().strip())
