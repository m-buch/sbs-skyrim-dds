# sbsdesigner-skyrim-dds

One-button export from Substance 3D Designer to properly formatted DDS files for Skyrim SE.

## Layout

- `tools/skydds/` — CLI wrapping [Cuttlefish](https://github.com/akb825/Cuttlefish)
  (submodule at `external/Cuttlefish`, pinned to v2.9.0). The Designer plugin talks
  only to this binary, never to Cuttlefish directly.
- `plugin/skyrim_dds_export/` — the Designer Python plugin.

## Building skydds (Windows / MSVC)

```
git clone --recursive <this repo>
cmake --preset msvc
cmake --build --preset release
```

Output lands in `build/tools/skydds/Release/skydds.exe`. ISPC is not set up yet.

## Python side

Managed with [uv](https://docs.astral.sh/uv/); lint/format with ruff:

```
uv sync
uv run ruff check plugin tests
uv run pytest
```
