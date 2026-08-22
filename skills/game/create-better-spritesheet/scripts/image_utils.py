"""Compatibility exports for internal premultiplied-alpha image helpers."""

from spritesheet_core.rendering import (
    HIGH_RESOLUTION_SHORT_SIDE,
    MAX_HIGH_RESOLUTION_SIDE,
    MAX_TARGET_SIDE,
    clear_transparent_rgb,
    from_premultiplied,
    resize_premultiplied,
    resolve_high_resolution_dimensions,
    round_ratio,
    to_premultiplied,
)

__all__ = [
    "HIGH_RESOLUTION_SHORT_SIDE",
    "MAX_HIGH_RESOLUTION_SIDE",
    "MAX_TARGET_SIDE",
    "clear_transparent_rgb",
    "from_premultiplied",
    "resize_premultiplied",
    "resolve_high_resolution_dimensions",
    "round_ratio",
    "to_premultiplied",
]
