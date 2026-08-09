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


def convert(images, tmp_path, src, fmt, colorspace, alpha, *extra):
    """Runs a conversion."""
    out = tmp_path / "out.dds"
    result = run(
        "--in",
        str(images / src),
        "--out",
        str(out),
        "--format",
        fmt,
        "--colorspace",
        colorspace,
        "--alpha",
        alpha,
        *extra,
    )
    assert result.returncode == 0, result.stderr
    return dds_header(out)


def test_normal_map_settings(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "bc7", "linear", "encoded")
    assert header["fourcc"] == b"DX10"
    assert header["dxgi"] == DXGI_BC7_UNORM
    assert header["mips"] == 10
    assert header["misc_flags2"] & 0x7 == 0  # alpha mode Unknown like vanilla


def test_diffuse_settings(images, tmp_path):
    header = convert(images, tmp_path, "opaque.png", "bc1", "srgb", "blend")
    assert header["dxgi"] == DXGI_BC1_UNORM



def test_bc1a_punchthrough(images, tmp_path):
    header = convert(images, tmp_path, "translucent.png", "bc1a", "srgb", "blend")
    assert header["dxgi"] == DXGI_BC1_UNORM  # BC1a shares the BC1_UNORM tag


def test_bc4_single_channel(images, tmp_path):
    header = convert(images, tmp_path, "gray.png", "bc4", "linear", "none")
    assert header["dxgi"] == DXGI_BC4_UNORM
    assert header["mips"] == 9


def test_resize_pow2(images, tmp_path):
    header = convert(images, tmp_path, "npot.png", "bc1", "srgb", "blend", "--resize", "pow2")
    assert (header["width"], header["height"]) == (512, 512)


def test_dry_run_writes_nothing(images, tmp_path):
    out = tmp_path / "out.dds"
    result = run(
        "--in",
        str(images / "opaque.png"),
        "--out",
        str(out),
        "--format",
        "bc1",
        "--colorspace",
        "srgb",
        "--alpha",
        "test",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "BC1" in result.stdout
    assert not out.exists()


def test_dry_run_reports_resolved_settings(images, tmp_path):
    out = tmp_path / "out.dds"
    result = run(
        "--in",
        str(images / "translucent.png"),
        "--out",
        str(out),
        "--format",
        "bc7",
        "--colorspace",
        "linear",
        "--alpha",
        "encoded",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "linear" in result.stdout
    assert "encoded" in result.stdout


@pytest.mark.parametrize(
    "missing",
    [
        ("--colorspace", "srgb", "--alpha", "blend"),
        ("--format", "bc1", "--alpha", "blend"),
        ("--format", "bc1", "--colorspace", "srgb"),
    ],
)
def test_each_encoding_flag_is_required(images, tmp_path, missing):
    result = run("--in", str(images / "opaque.png"), "--out", str(tmp_path / "out.dds"), *missing)
    assert result.returncode == 2
    assert "is required" in result.stderr


def test_bad_format_value_fails(images, tmp_path):
    result = run(
        "--in",
        str(images / "opaque.png"),
        "--out",
        str(tmp_path / "out.dds"),
        "--format",
        "astc",
        "--colorspace",
        "srgb",
        "--alpha",
        "none",
    )
    assert result.returncode == 2


def test_alpha_ref_accepted_with_alpha_test(images, tmp_path):
    header = convert(
        images, tmp_path, "translucent.png", "bc7", "srgb", "test", "--alpha-ref", "0.35"
    )
    assert header["dxgi"] == DXGI_BC7_UNORM


def test_dry_run_reports_coverage_for_alpha_test(images, tmp_path):
    out = tmp_path / "out.dds"
    result = run(
        "--in",
        str(images / "translucent.png"),
        "--out",
        str(out),
        "--format",
        "bc7",
        "--colorspace",
        "srgb",
        "--alpha",
        "test",
        "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    assert "cover" in result.stdout


@pytest.mark.parametrize("bad", ["0", "1", "-0.5", "1.5", "half"])
def test_alpha_ref_range_is_validated(images, tmp_path, bad):
    result = run(
        "--in",
        str(images / "translucent.png"),
        "--out",
        str(tmp_path / "out.dds"),
        "--format",
        "bc7",
        "--colorspace",
        "srgb",
        "--alpha",
        "test",
        "--alpha-ref",
        bad,
    )
    assert result.returncode == 2


def test_slot_flag_is_gone(images, tmp_path):
    result = run(
        "--in",
        str(images / "opaque.png"),
        "--out",
        str(tmp_path / "out.dds"),
        "--slot",
        "diffuse",
    )
    assert result.returncode == 2
    assert "unknown argument" in result.stderr
