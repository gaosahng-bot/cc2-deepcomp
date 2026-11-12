from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepcomp import composite as C
from deepcomp.crypto_hash import crypto_id
from deepcomp.flat import read_flat
from deepcomp.format import Sample, empty_image, read_deep, set_pixel, write_deep

FIXTURES = ROOT / "fixtures"
EPS = 1e-5


def _flatten_files(inputs, holdout=None, isolate=None):
    import subprocess

    out = Path("/tmp/dc_pytest_out.flat")
    cmd = [sys.executable, "-m", "deepcomp", "composite", "--flatten", str(out)]
    cmd += ["--inputs", *[str(p) for p in inputs]]
    if holdout is not None:
        cmd += ["--holdout", str(holdout)]
    if isolate is not None:
        cmd += ["--isolate", isolate]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    _, _, pixels = read_flat(out)
    return pixels


def _px(pixels, x, y, width=8):
    return pixels[y * width + x]


def _close(got, want, eps=EPS):
    assert len(got) == len(want)
    assert all(abs(a - b) <= eps for a, b in zip(got, want)), (got, want)


def test_backdrop_only():
    pixels = _flatten_files([FIXTURES / "backdrop.deep"])
    for px in pixels:
        _close(px, (0.0, 0.0, 0.4, 1.0))


def test_hero_over_backdrop():
    pixels = _flatten_files([FIXTURES / "hero.deep", FIXTURES / "backdrop.deep"])
    _close(_px(pixels, 3, 2), (0.8, 0.1, 0.04, 1.0))
    _close(_px(pixels, 0, 0), (0.0, 0.0, 0.4, 1.0))


def test_holdout_blocks_same_depth_color():
    pixels = _flatten_files(
        [FIXTURES / "hero.deep", FIXTURES / "backdrop.deep"],
        holdout=FIXTURES / "holdout.deep",
    )
    _close(_px(pixels, 3, 2), (0.0, 0.0, 0.0, 1.0))
    _close(_px(pixels, 0, 0), (0.0, 0.0, 0.4, 1.0))


def test_isolate_keeps_named_color_only():
    pixels = _flatten_files(
        [FIXTURES / "hero.deep", FIXTURES / "backdrop.deep"],
        isolate="hero",
    )
    _close(_px(pixels, 3, 2), (0.8, 0.1, 0.0, 0.9))
    _close(_px(pixels, 0, 0), (0.0, 0.0, 0.0, 0.0))


def test_overlap_fixture():
    pixels = _flatten_files([FIXTURES / "overlap.deep"])
    _close(_px(pixels, 1, 1), (0.5, 0.0, 0.25, 0.75))
    _close(_px(pixels, 4, 1), (0.4, 0.0, 0.24, 1.0))
    _close(_px(pixels, 6, 6), (0.0, 0.0, 0.0, 0.0))


def test_fog_over_backdrop():
    pixels = _flatten_files([FIXTURES / "fog.deep", FIXTURES / "backdrop.deep"])
    _close(_px(pixels, 0, 3), (0.0, 0.45, 0.31, 1.0))


def test_volume_split_rebuilds_original():
    name_id = crypto_id("hero")
    original = Sample(1.0, 5.0, 0.3, 0.2, 0.1, 0.7, 1.0, name_id)
    color = empty_image(1, 1)
    set_pixel(color, 0, 0, [original])
    # Invisible surfaces from another layer force interior cuts at z=2 and z=4.
    cutters = empty_image(1, 1)
    set_pixel(
        cutters,
        0,
        0,
        [
            Sample(2.0, 2.0, 0.0, 0.0, 0.0, 0.0, 1.0, name_id),
            Sample(4.0, 4.0, 0.0, 0.0, 0.0, 0.0, 1.0, name_id),
        ],
    )
    merged = C.merge_images([color, cutters])
    volume_pieces = [s for s in merged.pixels[0] if s.zback > s.zfront]
    assert len(volume_pieces) == 3
    flat = C.flatten_image(merged)[0]
    _close(flat, (original.r, original.g, original.b, original.a), eps=1e-12)


def test_coverage_is_baked_and_output_coverage_is_one():
    hero = crypto_id("hero")
    backdrop = crypto_id("backdrop")
    image = empty_image(1, 1)
    set_pixel(
        image,
        0,
        0,
        [
            Sample(1.0, 1.0, 0.8, 0.0, 0.0, 0.8, 0.5, hero),
            Sample(5.0, 5.0, 0.0, 0.0, 0.4, 1.0, 1.0, backdrop),
        ],
    )
    merged = C.merge_images([image])
    front = merged.pixels[0][0]
    assert front.coverage == 1.0
    assert abs(front.r - 0.4) < 1e-12
    assert abs(front.a - 0.4) < 1e-12


def test_unknown_isolate_is_empty_color():
    image = empty_image(1, 1)
    set_pixel(image, 0, 0, [Sample(1.0, 1.0, 0.2, 0.2, 0.2, 0.5, 1.0, crypto_id("hero"))])
    merged = C.merge_images([image], isolate_id=crypto_id("definitely_missing"))
    assert merged.sample_count() == 0
    assert C.flatten_image(merged)[0] == (0.0, 0.0, 0.0, 0.0)


def test_same_depth_order_follows_input_sequence():
    hero = crypto_id("hero")
    backdrop = crypto_id("backdrop")
    red = empty_image(1, 1)
    set_pixel(red, 0, 0, [Sample(2.0, 2.0, 0.6, 0.0, 0.0, 1.0, 1.0, hero)])
    green = empty_image(1, 1)
    set_pixel(green, 0, 0, [Sample(2.0, 2.0, 0.0, 0.7, 0.0, 1.0, 1.0, backdrop)])
    assert C.flatten_image(C.merge_images([red, green]))[0] == (0.6, 0.0, 0.0, 1.0)
    assert C.flatten_image(C.merge_images([green, red]))[0] == (0.0, 0.7, 0.0, 1.0)


def test_holdout_never_written_to_deep(tmp_path: Path):
    merged = C.merge_images([read_deep(FIXTURES / "hero.deep")])
    out = tmp_path / "merged.deep"
    write_deep(out, merged)
    reloaded = read_deep(out)
    holdout_id = crypto_id("holdout_card")
    assert all(s.crypto_id != holdout_id for bucket in reloaded.pixels for s in bucket)


def test_cli_errors_are_nonzero(tmp_path: Path):
    import subprocess

    def run(args):
        return subprocess.run(
            [sys.executable, "-m", "deepcomp", "composite", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    missing = run(["--inputs", str(tmp_path / "missing.deep"), "--flatten", str(tmp_path / "x.flat")])
    assert missing.returncode != 0 and missing.stderr

    bad = tmp_path / "bad.deep"
    bad.write_bytes(b"DCP1" + b"\x00" * 20)
    corrupt = run(["--inputs", str(bad), "--flatten", str(tmp_path / "x.flat")])
    assert corrupt.returncode != 0 and corrupt.stderr

    small_path = tmp_path / "small.deep"
    write_deep(small_path, empty_image(4, 4))
    mismatch = run(
        [
            "--inputs",
            str(FIXTURES / "hero.deep"),
            str(small_path),
            "--flatten",
            str(tmp_path / "x.flat"),
        ]
    )
    assert mismatch.returncode != 0 and "resolution mismatch" in mismatch.stderr


def test_apply_isolate_filters_samples():
    hero = crypto_id("hero")
    other = crypto_id("other")
    image = empty_image(1, 1)
    set_pixel(
        image,
        0,
        0,
        [
            Sample(1.0, 1.0, 0.1, 0.1, 0.1, 0.5, 1.0, hero),
            Sample(2.0, 2.0, 0.2, 0.2, 0.2, 0.5, 1.0, other),
        ],
    )
    filtered = C.apply_isolate(image, hero)
    assert len(filtered.pixels[0]) == 1
    assert filtered.pixels[0][0].crypto_id == hero

