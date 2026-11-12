from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepcomp.crypto_hash import crypto_id
from deepcomp.format import DeepImage, Sample, read_deep, write_deep


def test_roundtrip(tmp_path: Path) -> None:
    sample = Sample(1.0, 2.5, 0.1, 0.2, 0.3, 0.4, 1.0, crypto_id("hero"))
    image = DeepImage(width=2, height=1, pixels=[[sample], []])
    path = tmp_path / "t.deep"
    write_deep(path, image)
    loaded = read_deep(path)
    assert loaded.width == 2 and loaded.height == 1
    assert loaded.premultiplied
    got = loaded.pixel(0, 0)[0]
    assert got.zfront == sample.zfront and got.zback == sample.zback
    assert got.crypto_id == sample.crypto_id and got.coverage == sample.coverage
    packed = loaded.pixel(0, 0)[0]
    assert [round(x, 6) for x in (packed.r, packed.g, packed.b, packed.a)] == [round(x, 6) for x in (sample.r, sample.g, sample.b, sample.a)]
    assert loaded.pixel(1, 0) == []


def test_rejects_bad_magic(tmp_path: Path) -> None:
    path = tmp_path / "bad.deep"
    path.write_bytes(b"XXXX" + b"\x00" * 60)
    try:
        read_deep(path)
    except ValueError as exc:
        assert "magic" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
