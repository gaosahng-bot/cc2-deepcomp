from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepcomp.probe import probe_file


def test_probe_bundled_hero() -> None:
    info = probe_file(ROOT / "fixtures/hero.deep", ROOT / "fixtures/crypto_manifest.json")
    assert info["width"] == 8 and info["height"] == 8
    assert info["samples"] == 16
    assert info["surface_samples"] == 16
    assert info["volume_samples"] == 0
    assert info["pixels_with_samples"] == 16
    assert info["crypto"][0]["name"] == "hero"


def test_probe_overlap_counts() -> None:
    info = probe_file(ROOT / "fixtures/overlap.deep")
    assert info["pixels_with_samples"] == 2
    assert info["volume_samples"] == 2
    assert info["surface_samples"] == 2
