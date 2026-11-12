"""Deep merge, holdout, Cryptomatte isolate and front-to-back flatten.

The math here follows docs/compositing.md exactly; in particular coverage is
premultiplied into every sample before any other work, and volume samples are
uniform media split with ``alpha = 1 - (1 - alpha) ** t``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .format import DeepImage, Sample, empty_image

RGBA = Tuple[float, float, float, float]

# Within a shared depth interval holdout has to be composited before color, so
# it sorts first on the kind key.
KIND_HOLDOUT = 0
KIND_COLOR = 1

RGB_OVERFLOW_EPS = 1e-5


@dataclass(frozen=True)
class _Work:
    """Internal sample: coverage already baked into rgb/alpha."""

    zfront: float
    zback: float
    r: float
    g: float
    b: float
    alpha: float
    crypto_id: int
    kind: int
    layer: int
    order: int

    def sort_key(self) -> Tuple[float, float, int, int, int]:
        return (self.zfront, self.zback, self.kind, self.layer, self.order)


def _color_work(sample: Sample, layer: int, order: int) -> _Work:
    coverage = sample.coverage
    return _Work(
        sample.zfront,
        sample.zback,
        sample.r * coverage,
        sample.g * coverage,
        sample.b * coverage,
        sample.a * coverage,
        sample.crypto_id,
        KIND_COLOR,
        layer,
        order,
    )


def _holdout_work(sample: Sample, order: int) -> _Work:
    # Holdout only occludes: its color is discarded, but coverage still scales
    # the occlusion alpha.
    coverage = sample.coverage
    return _Work(
        sample.zfront,
        sample.zback,
        0.0,
        0.0,
        0.0,
        sample.a * coverage,
        sample.crypto_id,
        KIND_HOLDOUT,
        0,
        order,
    )


def _split_at_boundaries(work: _Work, boundaries: Sequence[float]) -> List[_Work]:
    """Cut one (possibly volume) work at every interior boundary.

    Uniform medium over [zfront, zback]: a sub-interval covering a depth
    fraction ``dt`` keeps ``alpha_piece = 1 - (1 - alpha) ** dt`` and its
    premultiplied rgb is scaled by ``alpha_piece / alpha``. Surface samples
    have no interior boundary and pass through untouched.
    """
    zfront, zback = work.zfront, work.zback
    if zback <= zfront:
        return [work]

    cuts = [z for z in boundaries if zfront < z < zback]
    if not cuts:
        return [work]

    span = zback - zfront
    survive = 1.0 - work.alpha
    pieces: List[_Work] = []
    previous_z = zfront
    previous_t = 0.0
    for boundary in cuts + [zback]:
        t = 1.0 if boundary == zback else (boundary - zfront) / span
        dt = t - previous_t
        piece_alpha = 1.0 - survive ** dt
        if work.alpha > 0.0:
            scale = piece_alpha / work.alpha
            piece_r = work.r * scale
            piece_g = work.g * scale
            piece_b = work.b * scale
        else:
            piece_r = piece_g = piece_b = 0.0
        pieces.append(
            _Work(
                previous_z,
                boundary,
                piece_r,
                piece_g,
                piece_b,
                piece_alpha,
                work.crypto_id,
                work.kind,
                work.layer,
                work.order,
            )
        )
        previous_z = boundary
        previous_t = t
    return pieces


def _cut_and_sort(works: Sequence[_Work]) -> List[_Work]:
    """Split every work on the union of all Z edges, then order the pieces."""
    if not works:
        return []
    boundaries = sorted({z for work in works for z in (work.zfront, work.zback)})
    pieces: List[_Work] = []
    for work in works:
        pieces.extend(_split_at_boundaries(work, boundaries))
    pieces.sort(key=lambda item: item.sort_key())
    return pieces


def merge_images(layers: Sequence[DeepImage], isolate_id: Optional[int] = None) -> DeepImage:
    """Merge color layers into one deep image.

    Merge color layers per pixel. Samples are sorted by
    ``(zfront, zback, input index, original order)`` and volume samples are
    cut on every Z edge in the pixel. ``isolate_id``, if given, keeps only
    color samples carrying that crypto_id. Holdout is never part of the merge.
    """
    if not layers:
        raise ValueError("merge_images needs at least one color layer")
    width = layers[0].width
    height = layers[0].height
    merged = empty_image(width, height, flags=layers[0].flags)

    for pixel_index in range(width * height):
        works: List[_Work] = []
        for layer_index, image in enumerate(layers):
            for order, sample in enumerate(image.pixels[pixel_index]):
                if isolate_id is not None and sample.crypto_id != isolate_id:
                    continue
                works.append(_color_work(sample, layer_index, order))

        pieces = _cut_and_sort(works)
        merged.pixels[pixel_index] = [
            Sample(
                piece.zfront,
                piece.zback,
                piece.r,
                piece.g,
                piece.b,
                piece.alpha,
                1.0,
                piece.crypto_id,
            )
            for piece in pieces
        ]
    return merged


def flatten_image(
    color: DeepImage,
    holdout: Optional[DeepImage] = None,
) -> List[RGBA]:
    """Front-to-back premultiplied over. Returns width*height RGBA tuples.

    Holdout samples contribute alpha only and, at equal depth, composite ahead
    of color. All samples (color plus holdout) share one union of Z edges so
    the per-pixel sequence is fully split before accumulation starts.
    """
    width = color.width
    height = color.height
    if holdout is not None and (holdout.width != width or holdout.height != height):
        raise ValueError("holdout resolution does not match the color image")

    pixels: List[RGBA] = []
    for pixel_index in range(width * height):
        works: List[_Work] = [
            _color_work(sample, layer=0, order=order)
            for order, sample in enumerate(color.pixels[pixel_index])
        ]
        if holdout is not None:
            works.extend(
                _holdout_work(sample, order)
                for order, sample in enumerate(holdout.pixels[pixel_index])
            )

        acc_r = acc_g = acc_b = 0.0
        acc_a = 0.0
        for piece in _cut_and_sort(works):
            pass_through = 1.0 - acc_a
            if piece.kind == KIND_COLOR:
                acc_r += piece.r * pass_through
                acc_g += piece.g * pass_through
                acc_b += piece.b * pass_through
            # Holdout pieces carry zero rgb and only add occlusion.
            acc_a += piece.alpha * pass_through

        clamped_a = min(1.0, max(0.0, acc_a))
        pixels.append(
            (
                _clamp_rgb_channel(acc_r),
                _clamp_rgb_channel(acc_g),
                _clamp_rgb_channel(acc_b),
                clamped_a,
            )
        )
    return pixels


def apply_isolate(image: DeepImage, crypto_id: int) -> DeepImage:
    """Return a copy that keeps only color samples with the given crypto_id."""
    filtered = empty_image(image.width, image.height, flags=image.flags)
    filtered.pixels = [
        [sample for sample in bucket if sample.crypto_id == crypto_id]
        for bucket in image.pixels
    ]
    return filtered


def _clamp_rgb_channel(value: float) -> float:
    # Normal premultiplied results stay untouched; only an obvious overshoot is
    # pulled back into range.
    if value > 1.0 + RGB_OVERFLOW_EPS:
        return 1.0
    return value
