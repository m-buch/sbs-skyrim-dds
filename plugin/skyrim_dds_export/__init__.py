"""Substance Designer plugin: export graph outputs to Skyrim SE DDS via skydds.

Install by copying/junctioning this package into:
%USERPROFILE%/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/
"""

import traceback

import sd

from . import exporter
from .export_dialog import ExportDialog
from .qt import QAction, QtGui, QtWidgets
from .settings import Settings, SettingsDialog

_ui_mgr = None
_callback_id = None
_toolbars = []
_shortcut_action = None


def _main_window():
    return _ui_mgr.getMainWindow() if _ui_mgr else None


def _graph_id(graph):
    try:
        url = graph.getUrl()
        if url:
            return str(url)
    except Exception:
        pass
    return str(graph.getIdentifier())


def _graph_name(graph):
    try:
        identifier = str(graph.getIdentifier())
        if identifier:
            return identifier
    except Exception:
        pass
    return "untitled"


def _run_export():
    try:
        graph = _ui_mgr.getCurrentGraph()
        if graph is None:
            QtWidgets.QMessageBox.warning(_main_window(), "Skyrim DDS Export", "No graph is open.")
            return

        settings = Settings()
        outputs = exporter.gather_outputs(graph)
        if not outputs:
            QtWidgets.QMessageBox.warning(
                _main_window(), "Skyrim DDS Export", "The current graph has no texture outputs."
            )
            return

        graph_id = _graph_id(graph)
        dialog = ExportDialog(
            _graph_name(graph), outputs, settings.graph_state(graph_id), _main_window()
        )
        accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
        if not accepted:
            return
        settings.set_graph_state(graph_id, dialog.state())

        results = exporter.export_items(
            graph,
            dialog.export_items(),
            settings.skydds_path,
            dialog.output_dir,
            dialog.alpha_mode,
        )
    except exporter.ExportError as error:
        QtWidgets.QMessageBox.warning(_main_window(), "Skyrim DDS Export", str(error))
        return
    except Exception:
        traceback.print_exc()
        QtWidgets.QMessageBox.critical(
            _main_window(), "Skyrim DDS Export", "Export failed:\n\n" + traceback.format_exc()
        )
        return

    failed = [r for r in results if not r.ok]
    lines = []
    for result in results:
        status = "ok" if result.ok else "FAILED"
        line = f"{status}  {result.name}"
        if result.message:
            line += "\n    " + result.message.replace("\n", "\n    ")
        lines.append(line)
        print("[skyrim_dds_export] " + line)

    if failed:
        QtWidgets.QMessageBox.warning(
            _main_window(),
            "Skyrim DDS Export",
            "{} of {} outputs failed:\n\n{}".format(len(failed), len(results), "\n".join(lines)),
        )


def _open_settings():
    dialog = SettingsDialog(Settings(), _main_window())
    dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()


def _on_graph_view_created(graph_view_id):
    toolbar = QtWidgets.QToolBar()
    export_action = toolbar.addAction("SkyDDS")
    export_action.setToolTip("Export outputs to Skyrim DDS... (Ctrl+Shift+D)")
    export_action.triggered.connect(_run_export)
    settings_action = toolbar.addAction("⚙")
    settings_action.setToolTip("Skyrim DDS Export settings (skydds.exe location)")
    settings_action.triggered.connect(_open_settings)
    _ui_mgr.addToolbarToGraphView(graph_view_id, toolbar, icon=None, tooltip="Skyrim DDS Export")
    _toolbars.append(toolbar)


def initializeSDPlugin():
    global _ui_mgr, _callback_id, _shortcut_action
    app = sd.getContext().getSDApplication()
    _ui_mgr = app.getQtForPythonUIMgr()
    _callback_id = _ui_mgr.registerGraphViewCreatedCallback(_on_graph_view_created)

    main_window = _main_window()
    if main_window is not None:
        _shortcut_action = QAction("Skyrim DDS Export", main_window)
        _shortcut_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+D"))
        _shortcut_action.triggered.connect(_run_export)
        main_window.addAction(_shortcut_action)
    print("[skyrim_dds_export] initialized")


def uninitializeSDPlugin():
    global _ui_mgr, _callback_id, _shortcut_action
    if _ui_mgr and _callback_id is not None:
        _ui_mgr.unregisterCallback(_callback_id)
    main_window = _main_window()
    if main_window is not None and _shortcut_action is not None:
        main_window.removeAction(_shortcut_action)
    _toolbars.clear()
    _shortcut_action = None
    _callback_id = None
    _ui_mgr = None
