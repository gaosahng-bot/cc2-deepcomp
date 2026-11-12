"""Deep merge, holdout and flatten.

These functions are intentionally unimplemented. Wire them up from the CLI
after you fill them in. The rules live in docs/compositing.md.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .format import DeepImage, Sample

RGBA = Tuple[float, float, float, float]


def merge_images(layers: Sequence[DeepImage], isolate_id: Optional[int] = None) -> DeepImage:
    """Merge color layers into one deep image.

    isolate_id, if given, keeps only samples with that crypto_id.
    """
    raise NotImplementedError("merge_images is not implemented yet")


def flatten_image(
    color: DeepImage,
    holdout: Optional[DeepImage] = None,
) -> List[RGBA]:
    """Front-to-back flatten. Returns width*height premultiplied RGBA tuples."""
    raise NotImplementedError("flatten_image is not implemented yet")


def apply_isolate(image: DeepImage, crypto_id: int) -> DeepImage:
    """Return a copy that keeps only samples with the given crypto_id."""
    raise NotImplementedError("apply_isolate is not implemented yet")
