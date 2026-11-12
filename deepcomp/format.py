"""DCP1 deep image I/O. See docs/format.md."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union

MAGIC = b"DCP1"
VERSION = 1
HEADER_SIZE = 64
INDEX_ENTRY_SIZE = 8
SAMPLE_SIZE = 32
FLAG_PREMULTIPLIED = 0x0001

PathLike = Union[str, Path]


@dataclass(frozen=True)
class Sample:
    zfront: float
    zback: float
    r: float
    g: float
    b: float
    a: float
    coverage: float
    crypto_id: int

    def as_tuple(self) -> Tuple[float, float, float, float, float, float, float, int]:
        return (
            self.zfront,
            self.zback,
            self.r,
            self.g,
            self.b,
            self.a,
            self.coverage,
            self.crypto_id,
        )


@dataclass
class DeepImage:
    width: int
    height: int
    pixels: List[List[Sample]]
    flags: int = FLAG_PREMULTIPLIED

    @property
    def premultiplied(self) -> bool:
        return bool(self.flags & FLAG_PREMULTIPLIED)

    def pixel(self, x: int, y: int) -> List[Sample]:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            raise IndexError(f"pixel ({x}, {y}) out of bounds {self.width}x{self.height}")
        return self.pixels[y * self.width + x]

    def iter_pixels(self) -> Iterable[Tuple[int, int, List[Sample]]]:
        for y in range(self.height):
            for x in range(self.width):
                yield x, y, self.pixel(x, y)

    def sample_count(self) -> int:
        return sum(len(p) for p in self.pixels)


def _pack_header(width: int, height: int, flags: int, index_off: int, sample_off: int, n_samples: int) -> bytes:
    header = bytearray(HEADER_SIZE)
    struct.pack_into("<4sHHHHHHIII", header, 0, MAGIC, VERSION, flags, width, height, SAMPLE_SIZE, 0, index_off, sample_off, n_samples)
    return bytes(header)


def write_deep(path: PathLike, image: DeepImage) -> None:
    path = Path(path)
    if image.width <= 0 or image.height <= 0:
        raise ValueError("width and height must be positive")
    if len(image.pixels) != image.width * image.height:
        raise ValueError("pixels length must equal width*height")

    index = bytearray()
    samples = bytearray()
    first = 0
    for bucket in image.pixels:
        index += struct.pack("<II", first, len(bucket))
        for s in bucket:
            if s.zback < s.zfront:
                raise ValueError(f"zback < zfront: {s}")
            samples += struct.pack(
                "<fffffffI",
                float(s.zfront),
                float(s.zback),
                float(s.r),
                float(s.g),
                float(s.b),
                float(s.a),
                float(s.coverage),
                int(s.crypto_id) & 0xFFFFFFFF,
            )
        first += len(bucket)

    index_off = HEADER_SIZE
    sample_off = HEADER_SIZE + len(index)
    header = _pack_header(image.width, image.height, image.flags, index_off, sample_off, first)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + index + samples)


def read_deep(path: PathLike) -> DeepImage:
    path = Path(path)
    data = path.read_bytes()
    if len(data) < HEADER_SIZE:
        raise ValueError(f"{path} is too small to be a DCP1 file")
    magic, version, flags, width, height, sample_size, _reserved, index_off, sample_off, n_samples = struct.unpack_from("<4sHHHHHHIII", data, 0)
    if magic != MAGIC:
        raise ValueError(f"{path} has bad magic {magic!r}")
    if version != VERSION:
        raise ValueError(f"{path} has unsupported version {version}")
    if sample_size != SAMPLE_SIZE:
        raise ValueError(f"{path} has unexpected sample size {sample_size}")
    if width == 0 or height == 0:
        raise ValueError(f"{path} has empty dimensions")

    n_pixels = width * height
    index_end = index_off + n_pixels * INDEX_ENTRY_SIZE
    if index_off < HEADER_SIZE or index_end > len(data):
        raise ValueError(f"{path} has a truncated pixel index")
    sample_end = sample_off + n_samples * SAMPLE_SIZE
    if sample_off < index_end or sample_end > len(data):
        raise ValueError(f"{path} has a truncated sample table")

    pixels: List[List[Sample]] = []
    for i in range(n_pixels):
        first, count = struct.unpack_from("<II", data, index_off + i * INDEX_ENTRY_SIZE)
        if first + count > n_samples:
            raise ValueError(f"{path} pixel {i} references samples outside the table")
        bucket: List[Sample] = []
        for j in range(count):
            zf, zb, r, g, b, a, cov, cid = struct.unpack_from("<fffffffI", data, sample_off + (first + j) * SAMPLE_SIZE)
            bucket.append(Sample(zf, zb, r, g, b, a, cov, cid))
        pixels.append(bucket)
    return DeepImage(width=width, height=height, pixels=pixels, flags=flags)


def empty_image(width: int, height: int, flags: int = FLAG_PREMULTIPLIED) -> DeepImage:
    return DeepImage(width=width, height=height, pixels=[[] for _ in range(width * height)], flags=flags)


def set_pixel(image: DeepImage, x: int, y: int, samples: Sequence[Sample]) -> None:
    image.pixels[y * image.width + x] = list(samples)
