from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepcomp.crypto_hash import crypto_id, crypto_id_hex


def test_stable_known_values() -> None:
    # Frozen values so a later hash change would break fixtures.
    assert crypto_id_hex("hero") == "3fbb5c59"
    assert crypto_id("hero") == int("3fbb5c59", 16)
    assert crypto_id("hero") != crypto_id("Hero")
    assert crypto_id("backdrop") != crypto_id("fog")
