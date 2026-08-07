# SkyDDS

One-button export from Substance 3D Designer to properly formatted DDS files for Skyrim SE.

## Installation

Extract the release zip into your ```Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins```
directory, or wherever else your sduserplugins are located. Make sure the plugin is enabled in
Tools -> Plugin Manager. `skydds.exe` is included inside the plugin folder.

## Usage
<img width="333" height="117" alt="image" src="https://github.com/user-attachments/assets/2d7632af-6785-452f-8cf9-95cd211036dc" />
<br>
<img width="776" height="398" alt="image" src="https://github.com/user-attachments/assets/0d0b20fd-4e51-4192-9ee7-ab14e1303928" />
<br>
<img width="778" height="749" alt="image" src="https://github.com/user-attachments/assets/a67198e8-25d8-4841-9829-5aac407b2f85" />



Select a graph in the Explorer and click **the Skyrim icon** on the Explorer toolbar (or press
Ctrl+Shift+D to export the current graph), assign outputs to the proper slots, set the output
directory, and export.

Output settings are saved per-graph. The Settings tab can be used to change default export settings globally and to create
user-defined presets.

## Packaging a release

```
cmake --build --preset release
uv run python tools/package_release.py --version 0.1.0
```

Produces `dist/skyrim_dds_export-<version>.zip` with the exe bundled.

## Layout

- `src/skydds/` — `skydds_core`: image loading (stb_image), mip
  generation (stb_image_resize2), BC1/BC1a/BC4/BC7 block encoding
  ([bc7enc_rdo](https://github.com/richgel999/bc7enc_rdo)'s rgbcx + bc7enc), our own BC1a encoder, and DDS header writing.
- `tools/skydds/` — the CLI.
- `plugin/skyrim_dds_export/` — the Designer Python plugin.

## Building skydds (Windows / MSVC)

```
git clone --recursive <this repo>
cmake --preset msvc
cmake --build --preset release
```

Output lands in `build/tools/skydds/Release/skydds.exe`. BC7 currently uses bc7enc
(modes 1/6).

## Python side

Managed with [uv](https://docs.astral.sh/uv/); lint/format with ruff:

```
uv sync
uv run ruff check plugin tests
uv run pytest
```
