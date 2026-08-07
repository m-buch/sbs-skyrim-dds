"""Per-graph export dialog: an Export tab and a Settings tab."""

import os

from . import exporter
from .qt import QtWidgets
from .settings import ALPHA_MODES, bundled_skydds, resolve_skydds
from .slots import default_suffixes, slot_names

UNASSIGNED = "(unassigned)"
INVALID_FILENAME_CHARS = '<>:"/\\|?*'


class _OutputRow:
    def __init__(self, output, checkbox, slot_combo, base_label, suffix_edit, ext_label):
        self.output = output
        self.checkbox = checkbox
        self.slot_combo = slot_combo
        self.base_label = base_label
        self.suffix_edit = suffix_edit
        self.ext_label = ext_label


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, graph_name, outputs, state, settings, parent=None):
        """outputs: list of exporter.GraphOutput. state: stored per-graph dict."""
        super().__init__(parent)
        self._settings = settings
        self._default_suffixes = default_suffixes()
        self._suffixes = {
            slot: settings.suffix_for(slot, self._default_suffixes) for slot in slot_names()
        }
        self._rows = []
        self.setWindowTitle("Skyrim DDS Export — " + graph_name)
        self.setMinimumWidth(620)

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

    def _resolved_suffix(self, slot):
        """The suffix a newly assigned row gets for this slot."""
        return self._suffixes.get(slot, "")

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
        grid.setHorizontalSpacing(4)
        slots = slot_names()
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

            # Filename: read-only base + editable suffix + read-only extension.
            base_label = QtWidgets.QLabel()
            suffix_edit = QtWidgets.QLineEdit()
            suffix_edit.setMaximumWidth(90)
            suffix_edit.setToolTip("Suffix for this output; defaults come from the Settings tab")
            if "suffix" in stored:
                suffix_edit.setText(stored["suffix"])
            elif slot in slots:
                suffix_edit.setText(self._resolved_suffix(slot))
            suffix_edit.textChanged.connect(self._update_previews)
            ext_label = QtWidgets.QLabel(".dds")

            name_row = QtWidgets.QHBoxLayout()
            name_row.setSpacing(0)
            name_row.addStretch(1)
            name_row.addWidget(base_label)
            name_row.addWidget(suffix_edit)
            name_row.addWidget(ext_label)

            grid.addWidget(checkbox, row_index, 0)
            grid.addWidget(slot_combo, row_index, 1)
            grid.addLayout(name_row, row_index, 2)

            row = _OutputRow(output, checkbox, slot_combo, base_label, suffix_edit, ext_label)
            slot_combo.currentTextChanged.connect(lambda _text, r=row: self._on_slot_changed(r))
            self._rows.append(row)

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

        suffix_box = QtWidgets.QGroupBox("Default filename suffixes")
        suffix_layout = QtWidgets.QVBoxLayout(suffix_box)
        suffix_grid = QtWidgets.QGridLayout()
        self._suffix_edits = {}
        for index, slot in enumerate(slot_names()):
            edit = QtWidgets.QLineEdit(self._resolved_suffix(slot))
            edit.setMaximumWidth(110)
            edit.setPlaceholderText("(none)")
            edit.textChanged.connect(lambda text, s=slot: self._on_global_suffix_changed(s, text))
            suffix_grid.addWidget(QtWidgets.QLabel(slot), index // 2, (index % 2) * 2)
            suffix_grid.addWidget(edit, index // 2, (index % 2) * 2 + 1)
            self._suffix_edits[slot] = edit
        reset = QtWidgets.QPushButton("Reset to defaults")
        reset.clicked.connect(self._reset_suffixes)
        reset_row = QtWidgets.QHBoxLayout()
        reset_row.addStretch(1)
        reset_row.addWidget(reset)
        suffix_layout.addLayout(suffix_grid)
        suffix_layout.addLayout(reset_row)

        layout = QtWidgets.QVBoxLayout(tab)
        layout.addLayout(form)
        layout.addWidget(suffix_box)
        layout.addStretch(1)
        self._update_skydds_status()
        return tab

    def _reset_suffixes(self):
        for slot, edit in self._suffix_edits.items():
            edit.setText(self._default_suffixes.get(slot, ""))

    def _on_global_suffix_changed(self, slot, text):
        """Follow the new default in rows still using the old one; rows the
        user has customised keep their own suffix."""
        new = text.strip()
        old = self._suffixes.get(slot, "")
        self._suffixes[slot] = new
        for row in self._rows:
            if row.slot_combo.currentText() == slot and row.suffix_edit.text().strip() == old:
                row.suffix_edit.setText(new)
        self._update_previews()

    def _on_slot_changed(self, row):
        slot = row.slot_combo.currentText()
        row.suffix_edit.setEnabled(slot != UNASSIGNED)
        if slot != UNASSIGNED:
            row.suffix_edit.setText(self._resolved_suffix(slot))
        self._update_previews()

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
        if row.slot_combo.currentText() == UNASSIGNED:
            return None
        return self._name_edit.text().strip() + row.suffix_edit.text().strip() + ".dds"

    def _update_previews(self):
        base = self._name_edit.text().strip()
        for row in self._rows:
            active = row.checkbox.isChecked() and row.slot_combo.currentText() != UNASSIGNED
            row.base_label.setText(base)
            row.base_label.setEnabled(active)
            row.suffix_edit.setEnabled(active)
            row.ext_label.setEnabled(active)

    def _warn(self, message):
        QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", message)

    def accept(self):
        self._settings.skydds_path = self._skydds_edit.text().strip()
        self._settings.suffix_overrides = {
            slot: edit.text().strip() for slot, edit in self._suffix_edits.items()
        }

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

        bad = [
            row.output.name
            for row in checked
            if any(char in row.suffix_edit.text() for char in INVALID_FILENAME_CHARS)
        ]
        if bad:
            self._warn(
                "These suffixes contain characters not allowed in filenames "
                f"({INVALID_FILENAME_CHARS}):\n\n" + "\n".join(bad)
            )
            return

        names = [self._file_name(row) for row in checked]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            self._warn(
                "Two or more outputs would write the same file:\n\n"
                + "\n".join(duplicates)
                + "\n\nGive them different suffixes."
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
                "suffix": row.suffix_edit.text().strip(),
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
