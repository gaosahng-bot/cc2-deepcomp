"""Cryptomatte-style identifier for a layer name.

The id is a 32-bit pattern that also decodes as a normal float32.
Do not replace this function; fixtures were hashed with it.
"""

from __future__ import annotations

FNV_OFFSET = 2166136261
FNV_PRIME = 16777619


def fnv1a_32(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFF
    return h


def crypto_id(name: str) -> int:
    """Return the u32 crypto id of a UTF-8 name."""
    h = fnv1a_32(name.encode("utf-8"))
    # Keep the sign bit and 23-bit mantissa; force exponent to 127 so the
    # value is a normal float in [1, 2) or [-2, -1).
    bits = (h & 0x807FFFFF) | (127 << 23)
    if (bits & 0x7FFFFF) == 0:
        bits |= 1
    return bits


def crypto_id_hex(name: str) -> str:
    return f"{crypto_id(name):08x}"
