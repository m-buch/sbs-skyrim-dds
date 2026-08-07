"""Export selected output nodes of a graph to Skyrim DDS via the skydds CLI."""

import json
import os
import shutil
import subprocess
import tempfile

from sd.api.sdproperty import SDPropertyCategory

try:
    from sd.api.sdtypetexture import SDTypeTexture
except ImportError:
    SDTypeTexture = None


class ExportError(Exception):
    pass


class GraphOutput:
    """One texture-valued output node of the graph."""

    def __init__(self, node, name):
        self.node = node
        self.name = name


class OutputResult:
    def __init__(self, name, ok, message=""):
        self.name = name
        self.ok = ok
        self.message = message


def _slots_data():
    path = os.path.join(os.path.dirname(__file__), "slots.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["slots"]


def slot_names():
    return list(_slots_data().keys())


def canonical_suffix(slot):
    """The suffix appended to the base filename for a slot (diffuse: none)."""
    suffixes = _slots_data()[slot]["suffixes"]
    return suffixes[0] if suffixes else ""


def _output_name(node):
    """User-facing output name: the 'identifier' annotation, else the node id."""
    try:
        value = node.getAnnotationPropertyValueFromId("identifier")
        if value:
            identifier = value.get()
            if identifier:
                return str(identifier)
    except Exception:
        pass
    return str(node.getIdentifier())


def _texture_output_property(node):
    """The node's texture-typed output property, or None for value outputs
    (float sliders like heightScale end up as output nodes for some reason)."""
    props = node.getDefinition().getProperties(SDPropertyCategory.Output)
    for prop in props:
        prop_type = prop.getType()
        if SDTypeTexture is not None:
            if isinstance(prop_type, SDTypeTexture):
                return prop
        elif prop_type is not None and "texture" in prop_type.getId().lower():
            return prop
    return None


def gather_outputs(graph):
    """Texture-valued outputs of the graph."""
    outputs = []
    nodes = graph.getOutputNodes()
    for i in range(nodes.getSize()):
        node = nodes.getItem(i)
        if _texture_output_property(node) is None:
            continue
        outputs.append(GraphOutput(node, _output_name(node)))
    return outputs


class ExportItem:
    """One output selected for export in the dialog."""

    def __init__(self, output, slot, file_name):
        self.output = output
        self.slot = slot
        self.file_name = file_name  # final .dds name, no directory


def export_items(graph, items, skydds_path, output_dir, alpha_mode, progress=None):
    """Computes the graph and exports each item. Returns a list of OutputResult.
    """
    if not skydds_path or not os.path.isfile(skydds_path):
        raise ExportError("skydds.exe not found — set its path on the Settings tab")
    if not output_dir:
        raise ExportError("no output directory chosen")
    os.makedirs(output_dir, exist_ok=True)

    graph.compute()
    results = []
    tmp_dir = tempfile.mkdtemp(prefix="skyrim_dds_export_")
    try:
        for index, item in enumerate(items):
            name = item.output.name
            if progress is not None and not progress(index, len(items), name):
                break
            prop = _texture_output_property(item.output.node)
            value = item.output.node.getPropertyValue(prop) if prop else None
            texture = value.get() if value else None
            if texture is None or not hasattr(texture, "save"):
                results.append(OutputResult(name, False, "output has no computed texture"))
                continue

            png = os.path.join(tmp_dir, name + ".png")
            texture.save(png)

            dds = os.path.join(output_dir, item.file_name)
            command = [skydds_path, "--in", png, "--out", dds, "--slot", item.slot]
            if item.slot == "diffuse" and alpha_mode != "auto":
                command += ["--alpha-mode", alpha_mode]

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.run(
                command, capture_output=True, text=True, creationflags=creationflags
            )
            stderr = proc.stderr.strip()
            if proc.returncode != 0:
                results.append(OutputResult(name, False, stderr or "skydds failed"))
            else:
                results.append(OutputResult(name, True, stderr))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return results
