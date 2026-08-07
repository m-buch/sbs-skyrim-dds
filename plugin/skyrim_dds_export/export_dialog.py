"""Per-graph export dialog: an Export tab and a Settings tab."""

import os

from . import exporter, presets
from .qt import QtCore, QtWidgets
from .settings import bundled_skydds, resolve_skydds

UNASSIGNED = "(unassigned)"
INVALID_FILENAME_CHARS = '<>:"/\\|?*'

# Preset columns shared by the settings tables and the export table's overrides.
SETTING_COLUMNS = (
    ("format", presets.FORMATS),
    ("colorspace", presets.COLORSPACES),
    ("alpha", presets.ALPHA_KINDS),
)


class NoScrollComboBox(QtWidgets.QComboBox):

    def wheelEvent(self, event):
        event.ignore()


def _combo(values, current):
    combo = NoScrollComboBox()
    combo.addItems(values)
    combo.setCurrentText(current)
    return combo


def _read_only(item):
    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
    return item


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, graph_name, outputs, state, settings, parent=None):
        """outputs: list of exporter.GraphOutput. state: stored per-graph dict."""
        super().__init__(parent)
        self._settings = settings
        self._presets = settings.all_presets()
        self.setWindowTitle("Skyrim DDS Export — " + graph_name)
        self.setMinimumWidth(780)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.addTab(self._build_export_tab(graph_name, outputs, state), "Export")
        self._tabs.addTab(self._build_settings_tab(), "Settings")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText("Export")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(buttons)

    # ----- export tab -------------------------------------------------------

    def _preset_names(self):
        return [preset["name"] for preset in self._presets]

    def _build_export_tab(self, graph_name, outputs, state):
        tab = QtWidgets.QWidget()

        self._dir_edit = QtWidgets.QLineEdit(state.get("output_dir", ""))
        browse = QtWidgets.QPushButton("...")
        browse.clicked.connect(self._browse_dir)
        dir_row = QtWidgets.QHBoxLayout()
        dir_row.addWidget(self._dir_edit)
        dir_row.addWidget(browse)

        self._name_edit = QtWidgets.QLineEdit(state.get("filename", "") or graph_name)

        form = QtWidgets.QFormLayout()
        form.addRow("Output directory:", dir_row)
        form.addRow("Base filename:", self._name_edit)

        self._outputs_table = QtWidgets.QTableWidget(0, 6)
        self._outputs_table.setHorizontalHeaderLabels(
            ["Output", "Preset", "Suffix", "Format", "Colour space", "Alpha"]
        )
        self._outputs_table.verticalHeader().setVisible(False)
        self._outputs_table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((160, 130, 90, 75, 105)):
            self._outputs_table.setColumnWidth(column, width)

        names = self._preset_names()
        stored_outputs = state.get("outputs", {})
        self._outputs = []
        for output in outputs:
            stored = stored_outputs.get(output.name, {})
            preset_name = stored.get("preset") or stored.get("slot") or ""
            preset = presets.find(self._presets, preset_name)
            values = dict(preset) if preset else {}

            row = self._outputs_table.rowCount()
            self._outputs_table.insertRow(row)
            self._outputs.append(output)

            item = QtWidgets.QTableWidgetItem(output.name)
            item.setFlags(
                QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            item.setCheckState(
                QtCore.Qt.Checked if stored.get("enabled", False) else QtCore.Qt.Unchecked
            )
            self._outputs_table.setItem(row, 0, item)

            preset_combo = _combo([UNASSIGNED] + names, preset_name if preset else UNASSIGNED)
            preset_combo.currentTextChanged.connect(lambda _t, r=row: self._on_preset_changed(r))
            self._outputs_table.setCellWidget(row, 1, preset_combo)

            suffix = stored.get("suffix", values.get("suffix", ""))
            self._outputs_table.setItem(row, 2, QtWidgets.QTableWidgetItem(suffix))
            for column, (key, choices) in enumerate(SETTING_COLUMNS, start=3):
                current = stored.get(key, values.get(key, choices[0]))
                self._outputs_table.setCellWidget(
                    row, column, _combo(choices, current if current in choices else choices[0])
                )

        layout = QtWidgets.QVBoxLayout(tab)
        layout.addLayout(form)
        layout.addWidget(self._outputs_table)
        return tab

    def _on_preset_changed(self, row):
        """Pull the preset's values into this row's override columns."""
        name = self._outputs_table.cellWidget(row, 1).currentText()
        preset = presets.find(self._presets, name)
        if preset is None:
            return
        self._outputs_table.item(row, 2).setText(preset["suffix"])
        for column, (key, _choices) in enumerate(SETTING_COLUMNS, start=3):
            self._outputs_table.cellWidget(row, column).setCurrentText(preset[key])

    def _row_settings(self, row):
        """The effective settings for an output row."""
        settings = {
            "name": self._outputs_table.cellWidget(row, 1).currentText(),
            "suffix": self._outputs_table.item(row, 2).text().strip(),
        }
        for column, (key, _choices) in enumerate(SETTING_COLUMNS, start=3):
            settings[key] = self._outputs_table.cellWidget(row, column).currentText()
        return settings

    def _is_checked(self, row):
        return self._outputs_table.item(row, 0).checkState() == QtCore.Qt.Checked

    def _file_name(self, row):
        return self._name_edit.text().strip() + self._row_settings(row)["suffix"] + ".dds"

    # ----- settings tab -----------------------------------------------------

    def _build_preset_table(self, preset_list, fixed_names):
        table = QtWidgets.QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Name", "Suffix", "Format", "Colour space", "Alpha"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        for column, width in enumerate((150, 90, 75, 105)):
            table.setColumnWidth(column, width)
        for preset in preset_list:
            self._append_preset_row(table, preset, fixed_names)
        return table

    def _append_preset_row(self, table, preset, fixed_name):
        row = table.rowCount()
        table.insertRow(row)
        name_item = QtWidgets.QTableWidgetItem(preset["name"])
        if fixed_name:
            _read_only(name_item)
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, QtWidgets.QTableWidgetItem(preset["suffix"]))
        for column, (key, choices) in enumerate(SETTING_COLUMNS, start=2):
            table.setCellWidget(row, column, _combo(choices, preset[key]))

    @staticmethod
    def _table_presets(table):
        result = []
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            suffix_item = table.item(row, 1)
            preset = {
                "name": name_item.text().strip() if name_item else "",
                "suffix": suffix_item.text().strip() if suffix_item else "",
            }
            for column, (key, _choices) in enumerate(SETTING_COLUMNS, start=2):
                preset[key] = table.cellWidget(row, column).currentText()
            result.append(preset)
        return result

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
        exe_row = QtWidgets.QHBoxLayout()
        exe_row.addWidget(self._skydds_edit)
        exe_row.addWidget(browse)
        exe_row.addWidget(clear)

        self._skydds_status = QtWidgets.QLabel()
        self._skydds_status.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.addRow("skydds.exe override:", exe_row)
        form.addRow("", self._skydds_status)

        # Built-in presets
        defaults_box = QtWidgets.QGroupBox("Default presets")
        self._defaults_table = self._build_preset_table(self._settings.default_presets, True)
        self._defaults_table.setMinimumHeight(200)
        restore = QtWidgets.QPushButton("Restore defaults")
        restore.setToolTip("Discard edits to the built-in presets")
        restore.clicked.connect(self._restore_defaults)
        defaults_buttons = QtWidgets.QHBoxLayout()
        defaults_buttons.addStretch(1)
        defaults_buttons.addWidget(restore)
        defaults_layout = QtWidgets.QVBoxLayout(defaults_box)
        defaults_layout.addWidget(self._defaults_table)
        defaults_layout.addLayout(defaults_buttons)

        user_box = QtWidgets.QGroupBox("User presets")
        self._user_table = self._build_preset_table(self._settings.user_presets, False)
        self._user_table.setMinimumHeight(140)
        add = QtWidgets.QPushButton("Add")
        add.clicked.connect(self._add_user_preset)
        remove = QtWidgets.QPushButton("Remove")
        remove.clicked.connect(self._remove_user_preset)
        user_buttons = QtWidgets.QHBoxLayout()
        user_buttons.addWidget(add)
        user_buttons.addWidget(remove)
        user_buttons.addStretch(1)
        user_layout = QtWidgets.QVBoxLayout(user_box)
        user_layout.addWidget(self._user_table)
        user_layout.addLayout(user_buttons)

        layout = QtWidgets.QVBoxLayout(tab)
        layout.addLayout(form)
        layout.addWidget(defaults_box)
        layout.addWidget(user_box)
        self._update_skydds_status()
        return tab

    def _restore_defaults(self):
        self._defaults_table.setRowCount(0)
        for preset in presets.normalize_all(presets.default_presets()):
            self._append_preset_row(self._defaults_table, preset, True)

    def _add_user_preset(self):
        self._append_preset_row(
            self._user_table,
            {
                "name": "new_preset",
                "suffix": "_x",
                "format": "bc7",
                "colorspace": "linear",
                "alpha": "none",
            },
            False,
        )
        self._user_table.editItem(self._user_table.item(self._user_table.rowCount() - 1, 0))

    def _remove_user_preset(self):
        rows = sorted({index.row() for index in self._user_table.selectedIndexes()}, reverse=True)
        if not rows:
            self._warn("Select a user preset row to remove.")
            return
        for row in rows:
            self._user_table.removeRow(row)

    def _on_tab_changed(self, index):
        if index == 0:
            self._refresh_preset_choices()

    def _refresh_preset_choices(self):
        self._presets = presets.normalize_all(
            self._table_presets(self._defaults_table) + self._table_presets(self._user_table)
        )
        names = self._preset_names()
        for row in range(self._outputs_table.rowCount()):
            combo = self._outputs_table.cellWidget(row, 1)
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems([UNASSIGNED] + names)
            combo.setCurrentText(current if current in names else UNASSIGNED)
            combo.blockSignals(False)

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

    # ----- accept -----------------------------------------------------------

    def _warn(self, message):
        QtWidgets.QMessageBox.warning(self, "Skyrim DDS Export", message)

    def _save_global_settings(self):
        self._commit_open_editor()
        self._settings.skydds_path = self._skydds_edit.text().strip()
        self._settings.default_presets = self._table_presets(self._defaults_table)
        self._settings.user_presets = self._table_presets(self._user_table)

    def _commit_open_editor(self):
        for table in (self._defaults_table, self._user_table, self._outputs_table):
            editor_row = table.currentRow()
            editor_column = table.currentColumn()
            if editor_row >= 0 and editor_column >= 0:
                item = table.item(editor_row, editor_column)
                if item is not None:
                    table.closePersistentEditor(item)
        focus = self.focusWidget()
        if isinstance(focus, QtWidgets.QLineEdit):
            focus.clearFocus()

    def reject(self):
        self._save_global_settings()
        super().reject()

    def accept(self):
        self._refresh_preset_choices()
        self._save_global_settings()

        if not self._dir_edit.text().strip():
            self._warn("Choose an output directory.")
            return
        if not self._name_edit.text().strip():
            self._warn("Choose a base filename.")
            return

        checked = [row for row in range(self._outputs_table.rowCount()) if self._is_checked(row)]
        if not checked:
            self._warn("No outputs selected.")
            return

        unassigned = [
            self._outputs[row].name
            for row in checked
            if self._row_settings(row)["name"] == UNASSIGNED
        ]
        if unassigned:
            self._warn("These outputs have no preset assigned:\n\n" + "\n".join(unassigned))
            return

        bad = [
            self._outputs[row].name
            for row in checked
            if any(char in self._row_settings(row)["suffix"] for char in INVALID_FILENAME_CHARS)
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
        items = []
        for row in range(self._outputs_table.rowCount()):
            if not self._is_checked(row):
                continue
            settings = self._row_settings(row)
            if settings["name"] == UNASSIGNED:
                continue
            items.append(exporter.ExportItem(self._outputs[row], settings, self._file_name(row)))
        return items

    def state(self):
        """Dialog state to persist for this graph."""
        outputs = {}
        for row in range(self._outputs_table.rowCount()):
            settings = self._row_settings(row)
            name = settings.pop("name")
            settings["preset"] = "" if name == UNASSIGNED else name
            settings["enabled"] = self._is_checked(row)
            outputs[self._outputs[row].name] = settings
        return {
            "output_dir": self._dir_edit.text().strip(),
            "filename": self._name_edit.text().strip(),
            "outputs": outputs,
        }

    @property
    def output_dir(self):
        return os.path.normpath(self._dir_edit.text().strip())

    @property
    def skydds_path(self):
        return resolve_skydds(self._skydds_edit.text().strip())
