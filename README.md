# sbsdesigner-skyrim-dds

One-button export from Substance 3D Designer to properly formatted DDS files for Skyrim SE.

## Installation

Copy the skyrim_dds_export plugin to your ```Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins``` directory,
or to wherever else your sduserplugins are located. Make sure the plugin is enabled in the Tools -> Plugin Manager.

## Usage
<img width="558" height="359" alt="image" src="https://github.com/user-attachments/assets/bfa02257-34e5-4057-82e0-741fedb0a614" />

Click the cogwheel next to SkyDDS on your toolbar to set the skydds executable location.
When ready to export, click SkyDDS, assign outputs to the proper slots, set output directory, and export.

Output settings are saved per-graph.

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
