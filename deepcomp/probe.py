"""Summarize a DCP1 deep image."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from .format import DeepImage, read_deep

PathLike = Union[str, Path]


def load_manifest(path: PathLike) -> Dict[int, str]:
    raw = json.loads(Path(path).read_text())
    mapping: Dict[int, str] = {}
    # Accept {"name": "a1b2c3d4"} or {"name": 123}
    items = raw.get("ids", raw) if isinstance(raw, dict) else {}
    if not isinstance(items, dict):
        raise ValueError("manifest must be an object of name -> id")
    for name, value in items.items():
        if name in {"version", "ids"} and isinstance(value, dict):
            continue
        if isinstance(value, str):
            mapping[int(value, 16)] = name
        else:
            mapping[int(value)] = name
    return mapping


def probe_image(image: DeepImage, manifest: Optional[Mapping[int, str]] = None) -> Dict[str, Any]:
    counts = [len(p) for p in image.pixels]
    zmin = None
    zmax = None
    vol = 0
    surf = 0
    ids: Counter[int] = Counter()
    pixels_with = 0
    for bucket in image.pixels:
        if bucket:
            pixels_with += 1
        for s in bucket:
            zmin = s.zfront if zmin is None else min(zmin, s.zfront)
            zmax = s.zback if zmax is None else max(zmax, s.zback)
            if s.zback > s.zfront:
                vol += 1
            else:
                surf += 1
            ids[s.crypto_id] += 1

    crypto = []
    for cid, n in sorted(ids.items(), key=lambda kv: (-kv[1], kv[0])):
        entry: Dict[str, Any] = {"id": f"{cid:08x}", "id_u32": cid, "samples": n}
        if manifest and cid in manifest:
            entry["name"] = manifest[cid]
        crypto.append(entry)

    return {
        "width": image.width,
        "height": image.height,
        "premultiplied": image.premultiplied,
        "pixels": image.width * image.height,
        "pixels_with_samples": pixels_with,
        "samples": image.sample_count(),
        "surface_samples": surf,
        "volume_samples": vol,
        "min_samples_per_pixel": min(counts) if counts else 0,
        "max_samples_per_pixel": max(counts) if counts else 0,
        "z_min": zmin,
        "z_max": zmax,
        "crypto": crypto,
    }


def probe_file(path: PathLike, manifest_path: Optional[PathLike] = None) -> Dict[str, Any]:
    image = read_deep(path)
    manifest = load_manifest(manifest_path) if manifest_path else None
    result = probe_image(image, manifest)
    result["input"] = str(path)
    return result
