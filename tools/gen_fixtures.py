#!/usr/bin/env python3
"""Generate the bundled deep-image fixtures. This script only writes inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepcomp.crypto_hash import crypto_id, crypto_id_hex
from deepcomp.format import DeepImage, Sample, empty_image, set_pixel, write_deep

WIDTH = 8
HEIGHT = 8
NAMES = ("backdrop", "hero", "fog", "holdout_card")


def surface(z, r, g, b, a, name, coverage=1.0) -> Sample:
    return Sample(z, z, r, g, b, a, coverage, crypto_id(name))


def volume(zf, zb, r, g, b, a, name, coverage=1.0) -> Sample:
    return Sample(zf, zb, r, g, b, a, coverage, crypto_id(name))


def write_manifest(path: Path) -> None:
    ids = {name: crypto_id_hex(name) for name in NAMES}
    path.write_text(json.dumps({"version": 1, "ids": ids}, indent=2) + "\n")


def build_backdrop() -> DeepImage:
    img = empty_image(WIDTH, HEIGHT)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            set_pixel(img, x, y, [surface(10.0, 0.0, 0.0, 0.4, 1.0, "backdrop")])
    return img


def build_hero() -> DeepImage:
    img = empty_image(WIDTH, HEIGHT)
    # 4x4 square in the middle.
    for y in range(2, 6):
        for x in range(2, 6):
            set_pixel(img, x, y, [surface(2.0, 0.8, 0.1, 0.0, 0.9, "hero")])
    return img


def build_fog() -> DeepImage:
    img = empty_image(WIDTH, HEIGHT)
    # A horizontal slab that overlaps the hero in Z and in X/Y.
    for y in range(3, 5):
        for x in range(WIDTH):
            set_pixel(img, x, y, [volume(1.5, 4.0, 0.0, 0.45, 0.15, 0.6, "fog")])
    return img


def build_holdout() -> DeepImage:
    img = empty_image(WIDTH, HEIGHT)
    # Same footprint and depth as the hero, fully opaque.
    for y in range(2, 6):
        for x in range(2, 6):
            set_pixel(img, x, y, [surface(2.0, 1.0, 1.0, 1.0, 1.0, "holdout_card")])
    return img


def build_overlap() -> DeepImage:
    """A one-file stress pixel plus a couple of quiet neighbors, all 8x8."""
    img = empty_image(WIDTH, HEIGHT)
    # (1, 1): two overlapping volumes, used to check interval splits.
    set_pixel(
        img,
        1,
        1,
        [
            volume(1.0, 3.0, 0.5, 0.0, 0.0, 0.5, "hero"),
            volume(2.0, 4.0, 0.0, 0.0, 0.5, 0.5, "fog"),
        ],
    )
    # (4, 1): surface with coverage 0.5 in front of a backdrop-like surface.
    set_pixel(
        img,
        4,
        1,
        [
            surface(1.0, 0.8, 0.0, 0.0, 0.8, "hero", coverage=0.5),
            surface(5.0, 0.0, 0.0, 0.4, 1.0, "backdrop"),
        ],
    )
    # (6, 6): empty on purpose.
    return img


def main() -> int:
    out = ROOT / "fixtures"
    out.mkdir(parents=True, exist_ok=True)
    write_manifest(out / "crypto_manifest.json")
    write_deep(out / "backdrop.deep", build_backdrop())
    write_deep(out / "hero.deep", build_hero())
    write_deep(out / "fog.deep", build_fog())
    write_deep(out / "holdout.deep", build_holdout())
    write_deep(out / "overlap.deep", build_overlap())
    print(f"wrote fixtures into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
