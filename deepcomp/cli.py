"""Command line entry points. Parameter names are fixed; do not rename them."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import crypto_hash
from . import flat as flatmod
from . import probe as probe_mod
from .format import DeepImage, read_deep, write_deep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deepcomp", description="Deep image probe and compositor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe", help="summarize a .deep file")
    p_probe.add_argument("--input", required=True, help="path to a DCP1 .deep file")
    p_probe.add_argument("--manifest", help="optional JSON name->id map")
    p_probe.add_argument("--json", action="store_true", help="print a JSON object instead of text")

    p_comp = sub.add_parser("composite", help="merge, hold out, isolate and flatten")
    p_comp.add_argument("--inputs", nargs="+", required=True, help="one or more color .deep files, front-to-back priority for ties")
    p_comp.add_argument("--holdout", help="optional holdout .deep (occlusion only)")
    p_comp.add_argument("--isolate", help="optional Cryptomatte name to keep from color layers")
    p_comp.add_argument("--out-deep", dest="out_deep", help="write merged (and isolated) color deep image")
    p_comp.add_argument("--flatten", help="write FLT1 2D premultiplied RGBA")
    p_comp.add_argument("--preview", help="optional binary PPM preview")
    p_comp.add_argument("--report", help="write a JSON report")
    p_comp.add_argument("--manifest", help="optional JSON name->id map, used in the report")
    return parser


def _print_probe_text(info: dict) -> None:
    print(f"file: {info.get('input', '')}")
    print(f"size: {info['width']}x{info['height']}")
    print(f"premultiplied: {info['premultiplied']}")
    print(
        "samples: {samples} (surface {surface_samples}, volume {volume_samples}) over {pixels_with_samples}/{pixels} pixels".format(
            **info
        )
    )
    print(f"per-pixel: min {info['min_samples_per_pixel']}, max {info['max_samples_per_pixel']}")
    print(f"z range: {info['z_min']} .. {info['z_max']}")
    print("crypto:")
    for item in info["crypto"]:
        name = f"  {item['name']}" if "name" in item else ""
        print(f"  {item['id']}  samples={item['samples']}{name}")


def cmd_probe(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        print(f"input not found: {path}", file=sys.stderr)
        return 2
    try:
        info = probe_mod.probe_file(path, args.manifest)
    except Exception as exc:
        print(f"failed to probe {path}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        _print_probe_text(info)
    return 0


def cmd_composite(args: argparse.Namespace) -> int:
    # Import late so probe keeps working before composite is filled in.
    from . import composite as composite_mod

    if not args.out_deep and not args.flatten and not args.preview and not args.report:
        print("composite needs at least one of --out-deep / --flatten / --preview / --report", file=sys.stderr)
        return 2

    layers: List[DeepImage] = []
    for item in args.inputs:
        path = Path(item)
        if not path.is_file():
            print(f"input not found: {path}", file=sys.stderr)
            return 2
        try:
            layers.append(read_deep(path))
        except Exception as exc:
            print(f"failed to read {path}: {exc}", file=sys.stderr)
            return 2

    width, height = layers[0].width, layers[0].height
    for path, image in zip(args.inputs, layers):
        if image.width != width or image.height != height:
            print(f"resolution mismatch: {path} is {image.width}x{image.height}, expected {width}x{height}", file=sys.stderr)
            return 2

    holdout = None
    if args.holdout:
        hpath = Path(args.holdout)
        if not hpath.is_file():
            print(f"holdout not found: {hpath}", file=sys.stderr)
            return 2
        try:
            holdout = read_deep(hpath)
        except Exception as exc:
            print(f"failed to read holdout {hpath}: {exc}", file=sys.stderr)
            return 2
        if holdout.width != width or holdout.height != height:
            print(f"holdout resolution mismatch: {holdout.width}x{holdout.height}, expected {width}x{height}", file=sys.stderr)
            return 2

    isolate_id: Optional[int] = None
    if args.isolate is not None:
        isolate_id = crypto_hash.crypto_id(args.isolate)

    try:
        merged = composite_mod.merge_images(layers, isolate_id=isolate_id)
        flat_pixels = None
        if args.flatten or args.preview or args.report:
            flat_pixels = composite_mod.flatten_image(merged, holdout=holdout)
    except NotImplementedError as exc:
        print(f"composite is not implemented: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"composite failed: {exc}", file=sys.stderr)
        return 2

    if merged.width != width or merged.height != height:
        print("merge returned an image with a different resolution", file=sys.stderr)
        return 2

    if args.out_deep:
        try:
            write_deep(args.out_deep, merged)
        except Exception as exc:
            print(f"failed to write {args.out_deep}: {exc}", file=sys.stderr)
            return 2

    if flat_pixels is not None and len(flat_pixels) != width * height:
        print("flatten returned the wrong number of pixels", file=sys.stderr)
        return 2

    if args.flatten:
        try:
            flatmod.write_flat(args.flatten, width, height, flat_pixels)
        except Exception as exc:
            print(f"failed to write {args.flatten}: {exc}", file=sys.stderr)
            return 2

    if args.preview:
        try:
            flatmod.write_preview_ppm(args.preview, width, height, flat_pixels)
        except Exception as exc:
            print(f"failed to write {args.preview}: {exc}", file=sys.stderr)
            return 2

    if args.report:
        report = {
            "width": width,
            "height": height,
            "inputs": list(args.inputs),
            "holdout": args.holdout,
            "isolate": None,
            "out_deep": args.out_deep,
            "flatten": args.flatten,
            "preview": args.preview,
            "merged_samples": merged.sample_count(),
            "pixels_with_samples": sum(1 for p in merged.pixels if p),
            "max_samples_per_pixel": max((len(p) for p in merged.pixels), default=0),
        }
        if args.isolate is not None:
            report["isolate"] = {
                "name": args.isolate,
                "id": f"{isolate_id:08x}",
                "id_u32": isolate_id,
            }
        try:
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            print(f"failed to write {args.report}: {exc}", file=sys.stderr)
            return 2

    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "probe":
        return cmd_probe(args)
    if args.command == "composite":
        return cmd_composite(args)
    parser.error(f"unknown command {args.command}")
    return 2
