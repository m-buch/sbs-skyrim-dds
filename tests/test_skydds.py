"""Integration tests for the skydds CLI.

Requires a built skydds.exe.
"""

import struct
import subprocess
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]

DXGI_BC1_UNORM = 71
DXGI_BC4_UNORM = 80
DXGI_BC7_UNORM = 98


def find_skydds():
    for config in ("Release", "Debug"):
        exe = REPO / "build" / "tools" / "skydds" / config / "skydds.exe"
        if exe.exists():
            return exe
    return None


SKYDDS = find_skydds()
pytestmark = pytest.mark.skipif(SKYDDS is None, reason="skydds.exe not built")


def run(*args):
    return subprocess.run([str(SKYDDS), *args], capture_output=True, text=True)


def dds_header(path):
    data = path.read_bytes()
    assert data[:4] == b"DDS "
    height, width = struct.unpack_from("<II", data, 12)
    (mip_count,) = struct.unpack_from("<I", data, 28)
    fourcc = data[84:88]
    header = {"width": width, "height": height, "mips": mip_count, "fourcc": fourcc}
    if fourcc == b"DX10":
        header["dxgi"], _, _, _, header["misc_flags2"] = struct.unpack_from("<5I", data, 128)
    return header


@pytest.fixture(scope="session")
def images(tmp_path_factory):
    root = tmp_path_factory.mktemp("images")

    translucent = Image.new("RGBA", (512, 512))
    px = translucent.load()
    for y in range(512):
        for x in range(512):
            alpha = 255 if ((x // 32) + (y // 32)) % 2 == 0 else 96
            px[x, y] = (x % 256, y % 256, (x + y) % 256, alpha)
    translucent.save(root / "translucent.png")

    opaque = Image.new("RGBA", (512, 512), (180, 90, 45, 255))
    opaque.save(root / "opaque.png")

    gray = Image.new("L", (256, 256))
    px = gray.load()
    for y in range(256):
        for x in range(256):
            px[x, y] = (x ^ y) % 256
    gray.save(root / "gray.png")

    Image.new("RGB", (500, 300), (10, 200, 30)).save(root / "npot.png")
    return root


def convert(images, tmp_path, src, slot, *extra):
    out = tmp_path / "out.dds"
    result = run("--in", str(images / src), "--out", str(out), "--slot", slot, *extra)
    assert result.returncode == 0, result.stderr
    return dds_header(out)


def test_normal_bc7_unorm_spec_alpha(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "normal")
    assert header["fourcc"] == b"DX10"
    assert header["dxgi"] == DXGI_BC7_UNORM
    assert header["mips"] == 10  # full chain to 1x1
    assert header["misc_flags2"] & 0x7 == 0  # alpha mode Unknown like vanilla


def test_diffuse_opaque_picks_bc1(images, tmp_path):
    header = convert(images, tmp_path, "opaque.png", "diffuse")
    assert header["dxgi"] == DXGI_BC1_UNORM


def test_diffuse_translucent_picks_bc7(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "diffuse")
    assert header["dxgi"] == DXGI_BC7_UNORM


def test_diffuse_alpha_mode_test_picks_bc1a(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "diffuse", "--alpha-mode", "test")
    assert header["dxgi"] == DXGI_BC1_UNORM  # BC1a shares the BC1_UNORM tag


def test_diffuse_alpha_mode_none_forces_bc1(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "diffuse", "--alpha-mode", "none")
    assert header["dxgi"] == DXGI_BC1_UNORM


def test_diffuse_alpha_mode_blend_forces_bc7(images, tmp_path):
    header = convert(images, tmp_path, "opaque.png", "diffuse", "--alpha-mode", "blend")
    assert header["dxgi"] == DXGI_BC7_UNORM


def test_diffuse_auto_alpha_prints_notice(images, tmp_path):
    out = tmp_path / "out.dds"
    result = run("--in", str(images / "translucent.png"), "--out", str(out), "--slot", "diffuse")
    assert result.returncode == 0, result.stderr
    assert "alpha content detected" in result.stderr


def test_parallax_bc4(images, tmp_path):
    header = convert(images, tmp_path, "gray.png", "parallax")
    assert header["dxgi"] == DXGI_BC4_UNORM
    assert header["mips"] == 9


def test_resize_pow2(images, tmp_path):
    header = convert(images, tmp_path, "npot.png", "diffuse", "--resize", "pow2")
    assert (header["width"], header["height"]) == (512, 512)


def test_dry_run_writes_nothing(images, tmp_path):
    out = tmp_path / "out.dds"
    result = run(
        "--in", str(images / "opaque.png"), "--out", str(out), "--slot", "diffuse", "--dry-run"
    )
    assert result.returncode == 0, result.stderr
    assert "BC1" in result.stdout
    assert not out.exists()


def test_unknown_slot_fails(images, tmp_path):
    result = run(
        "--in", str(images / "opaque.png"), "--out", str(tmp_path / "out.dds"), "--slot", "specular"
    )
    assert result.returncode == 2
    assert "unknown slot" in result.stderr


def test_normal_rejects_alpha_mode(images, tmp_path):
    result = run(
        "--in",
        str(images / "translucent.png"),
        "--out",
        str(tmp_path / "out.dds"),
        "--slot",
        "normal",
        "--alpha-mode",
        "test",
    )
    assert result.returncode == 2
