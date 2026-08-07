"""Substance Designer plugin: export graph outputs to Skyrim SE DDS via skydds.

Install by copying/junctioning this package into:
%USERPROFILE%/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/
A skydds.exe placed inside this folder is found automatically.
"""

import os
import subprocess
import traceback

import sd
from sd.api.sdgraph import SDGraph

from . import exporter
from .export_dialog import ExportDialog
from .qt import QAction, QtCore, QtGui, QtWidgets
from .settings import Settings

TITLE = "Skyrim DDS Export"

_ui_mgr = None
_callback_ids = []
_widgets = []
_shortcut_action = None


def _main_window():
    return _ui_mgr.getMainWindow() if _ui_mgr else None


def _graph_id(graph):
    """Stable per-graph key for stored settings.

    Not getUrl(): it embeds a session-specific dependency id, so it changes
    every time Designer restarts. The package file path does not.
    """
    identifier = str(graph.getIdentifier())
    try:
        package_path = graph.getPackage().getFilePath()
        if package_path:
            return os.path.normcase(os.path.normpath(str(package_path))) + "::" + identifier
    except Exception:
        pass
    return identifier


def _graph_name(graph):
    try:
        identifier = str(graph.getIdentifier())
        if identifier:
            return identifier
    except Exception:
        pass
    return "untitled"


def _selected_explorer_graph(explorer_id):
    """The graph selected in the Explorer panel, if any."""
    try:
        selection = _ui_mgr.getExplorerSelection(explorer_id)
        for i in range(selection.getSize()):
            item = selection.getItem(i)
            if isinstance(item, SDGraph):
                return item
    except Exception:
        pass
    return None


def _show_results(results, output_dir):
    lines = []
    for result in results:
        status = "ok" if result.ok else "FAILED"
        line = f"{status}  {result.name}"
        if result.message:
            line += "\n    " + result.message.replace("\n", "\n    ")
        lines.append(line)
        print("[skyrim_dds_export] " + line)

    failed = [r for r in results if not r.ok]
    box = QtWidgets.QMessageBox(_main_window())
    box.setWindowTitle(TITLE)
    if failed:
        box.setIcon(QtWidgets.QMessageBox.Warning)
        box.setText(f"{len(failed)} of {len(results)} outputs failed.")
    else:
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.setText(f"Exported {len(results)} texture(s) to:\n{output_dir}")
    box.setDetailedText("\n".join(lines))
    open_button = box.addButton("Open folder", QtWidgets.QMessageBox.ActionRole)
    box.addButton(QtWidgets.QMessageBox.Close)
    box.exec_() if hasattr(box, "exec_") else box.exec()
    if box.clickedButton() is open_button and os.path.isdir(output_dir):
        subprocess.Popen(["explorer", os.path.normpath(output_dir)])


def _export_graph(graph):
    try:
        if graph is None:
            QtWidgets.QMessageBox.warning(_main_window(), TITLE, "No graph is open.")
            return

        settings = Settings()
        outputs = exporter.gather_outputs(graph)
        if not outputs:
            QtWidgets.QMessageBox.warning(
                _main_window(), TITLE, "This graph has no texture outputs."
            )
            return

        graph_id = _graph_id(graph)
        dialog = ExportDialog(
            _graph_name(graph), outputs, settings.graph_state(graph_id), settings, _main_window()
        )
        accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
        if not accepted:
            return
        settings.set_graph_state(graph_id, dialog.state())

        items = dialog.export_items()
        bar = QtWidgets.QProgressDialog("Exporting...", "Cancel", 0, len(items), _main_window())
        bar.setWindowTitle(TITLE)
        bar.setWindowModality(QtCore.Qt.WindowModal)
        bar.setMinimumDuration(0)

        def progress(done, total, name):
            bar.setValue(done)
            bar.setLabelText(f"Encoding {name} ({done + 1}/{total})...")
            QtWidgets.QApplication.processEvents()
            return not bar.wasCanceled()

        try:
            results = exporter.export_items(
                graph, items, dialog.skydds_path, dialog.output_dir, progress
            )
        finally:
            bar.close()
    except exporter.ExportError as error:
        QtWidgets.QMessageBox.warning(_main_window(), TITLE, str(error))
        return
    except Exception:
        traceback.print_exc()
        QtWidgets.QMessageBox.critical(
            _main_window(), TITLE, "Export failed:\n\n" + traceback.format_exc()
        )
        return

    if results:
        _show_results(results, dialog.output_dir)


def _export_current_graph():
    _export_graph(_ui_mgr.getCurrentGraph())


def _icon():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "skydds.svg")
    return QtGui.QIcon(path) if os.path.isfile(path) else QtGui.QIcon()


def _on_explorer_created(explorer_id):
    action = QAction(_icon(), "SkyDDS", _main_window())
    action.setToolTip("Export the selected graph to Skyrim DDS...")
    action.triggered.connect(
        lambda: _export_graph(_selected_explorer_graph(explorer_id) or _ui_mgr.getCurrentGraph())
    )
    _ui_mgr.addActionToExplorerToolbar(explorer_id, action)
    _widgets.append(action)


def initializeSDPlugin():
    global _ui_mgr, _shortcut_action
    app = sd.getContext().getSDApplication()
    _ui_mgr = app.getQtForPythonUIMgr()
    _callback_ids.append(_ui_mgr.registerExplorerCreatedCallback(_on_explorer_created))

    main_window = _main_window()
    if main_window is not None:
        _shortcut_action = QAction(TITLE, main_window)
        _shortcut_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+D"))
        _shortcut_action.triggered.connect(_export_current_graph)
        main_window.addAction(_shortcut_action)
    print("[skyrim_dds_export] initialized")


def uninitializeSDPlugin():
    global _ui_mgr, _shortcut_action
    if _ui_mgr:
        for callback_id in _callback_ids:
            _ui_mgr.unregisterCallback(callback_id)
    _callback_ids.clear()
    main_window = _main_window()
    if main_window is not None and _shortcut_action is not None:
        main_window.removeAction(_shortcut_action)
    _widgets.clear()
    _shortcut_action = None
    _ui_mgr = None
