"""Build a release zip: the plugin package with skydds.exe bundled inside it.

    uv run python tools/package_release.py [--version 0.1.0]

The zip extracts straight into Designer's sduserplugins folder.
"""

import argparse
import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin" / "skyrim_dds_export"
DIST = REPO / "dist"
SKIP = {"__pycache__", ".ruff_cache"}


def find_exe():
    for config in ("Release", "RelWithDebInfo", "Debug"):
        exe = REPO / "build" / "tools" / "skydds" / config / "skydds.exe"
        if exe.exists():
            return exe
    raise SystemExit("skydds.exe not found — run: cmake --build --preset release")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()

    exe = find_exe()
    staging = DIST / "skyrim_dds_export"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    for src in PLUGIN.rglob("*"):
        if any(part in SKIP for part in src.relative_to(PLUGIN).parts):
            continue
        dst = staging / src.relative_to(PLUGIN)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            shutil.copy2(src, dst)
    shutil.copy2(exe, staging / "skydds.exe")

    zip_path = DIST / f"skyrim_dds_export-{args.version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for src in staging.rglob("*"):
            if src.is_file():
                archive.write(src, src.relative_to(DIST))

    print(f"{zip_path}  ({zip_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
