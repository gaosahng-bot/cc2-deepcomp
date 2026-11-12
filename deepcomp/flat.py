"""Helpers for the FLT1 flat image container. Writing a finished image is still your job."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import List, Sequence, Tuple, Union

MAGIC = b"FLT1"
VERSION = 1
HEADER_SIZE = 64
PathLike = Union[str, Path]
Pixel = Tuple[float, float, float, float]


def write_flat(path: PathLike, width: int, height: int, pixels: Sequence[Pixel]) -> None:
    if len(pixels) != width * height:
        raise ValueError("pixels length must equal width*height")
    header = bytearray(HEADER_SIZE)
    struct.pack_into("<4sHHH", header, 0, MAGIC, VERSION, width, height)
    body = bytearray()
    for r, g, b, a in pixels:
        body += struct.pack("<ffff", float(r), float(g), float(b), float(a))
    Path(path).write_bytes(header + body)


def read_flat(path: PathLike) -> Tuple[int, int, List[Pixel]]:
    data = Path(path).read_bytes()
    if len(data) < HEADER_SIZE:
        raise ValueError(f"{path} is too small to be a FLT1 file")
    magic, version, width, height = struct.unpack_from("<4sHHH", data, 0)
    if magic != MAGIC:
        raise ValueError(f"{path} has bad magic {magic!r}")
    if version != VERSION:
        raise ValueError(f"{path} has unsupported version {version}")
    expected = HEADER_SIZE + width * height * 16
    if len(data) < expected:
        raise ValueError(f"{path} is truncated")
    pixels: List[Pixel] = []
    off = HEADER_SIZE
    for _ in range(width * height):
        pixels.append(struct.unpack_from("<ffff", data, off))
        off += 16
    return width, height, pixels


def write_preview_ppm(path: PathLike, width: int, height: int, pixels: Sequence[Pixel]) -> None:
    """Write a binary PPM using the un-premultiply rule in docs/compositing.md."""
    rows = [f"P6\n{width} {height}\n255\n".encode("ascii")]
    buf = bytearray()
    for r, g, b, a in pixels:
        if a <= 1e-6:
            ur = ug = ub = 0.0
        else:
            ur, ug, ub = r / a, g / a, b / a
        buf.append(int(round(min(1.0, max(0.0, ur)) * 255)))
        buf.append(int(round(min(1.0, max(0.0, ug)) * 255)))
        buf.append(int(round(min(1.0, max(0.0, ub)) * 255)))
    Path(path).write_bytes(rows[0] + buf)
