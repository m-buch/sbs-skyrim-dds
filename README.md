# sbsdesigner-skyrim-dds

One-button export from Substance 3D Designer to properly formatted DDS files for Skyrim SE.

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
