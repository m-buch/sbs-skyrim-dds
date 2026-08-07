"""Per-graph export dialog
"""

from . import exporter
from .qt import QtWidgets
from .settings import ALPHA_MODES

UNASSIGNED = "(unassigned)"


class _OutputRow:
    def __init__(self, output, checkbox, slot_combo, preview):
        self.output = output
        self.checkbox = checkbox
        self.slot_combo = slot_combo
        self.preview = preview


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, graph_name, outputs, state, parent=None):
        """outputs: list of exporter.GraphOutput. state: stored per-graph dict."""
        super().__init__(parent)
        self.setWindowTitle("Skyrim DDS Export — " + graph_name)
        self.setMinimumWidth(560)

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

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Export")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(outputs_box)
        layout.addWidget(buttons)
        self._update_previews()

    def _browse_dir(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Output directory (e.g. Data/textures/<mod>)", self._dir_edit.text()
        )
        if path:
            self._dir_edit.setText(path)

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

    def accept(self):
        if not self._dir_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", "Choose an output directory.")
            return
        if not self._name_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", "Choose a base filename.")
            return
        if not any(row.checkbox.isChecked() for row in self._rows):
            QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", "No outputs selected.")
            return
        unassigned = [
            row.output.name
            for row in self._rows
            if row.checkbox.isChecked() and row.slot_combo.currentText() == UNASSIGNED
        ]
        if unassigned:
            QtWidgets.QMessageBox.warning(
                self,
                "Skyrim DDS Export",
                "These outputs have no slot assigned:\n\n" + "\n".join(unassigned),
            )
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
        return self._dir_edit.text().strip()

    @property
    def alpha_mode(self):
        return self._alpha_combo.currentText()
