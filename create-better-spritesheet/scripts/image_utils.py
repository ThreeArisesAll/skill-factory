"""Shared premultiplied-alpha image helpers for spritesheet tools."""

from __future__ import annotations

import numpy as np
from PIL import Image

HIGH_RESOLUTION_SHORT_SIDE = 512
MAX_HIGH_RESOLUTION_SIDE = 16384
MAX_TARGET_SIDE = 4096


def to_premultiplied(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    alpha = rgba[..., 3:4]
    return np.concatenate((rgba[..., :3] * alpha, alpha), axis=2)


def from_premultiplied(array: np.ndarray) -> Image.Image:
    alpha = np.rint(np.clip(array[..., 3:4], 0.0, 1.0) * 255.0) / 255.0
    premultiplied_rgb = np.minimum(np.clip(array[..., :3], 0.0, 1.0), alpha)
    rgb = np.divide(
        premultiplied_rgb,
        alpha,
        out=np.zeros_like(premultiplied_rgb),
        where=alpha > 1e-6,
    )
    rgba = np.concatenate((rgb, alpha), axis=2)
    return Image.fromarray(np.rint(rgba * 255.0).astype(np.uint8), "RGBA")


def resize_premultiplied(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    premultiplied = to_premultiplied(image)
    resized_channels = []
    for channel in range(4):
        plane = Image.fromarray(premultiplied[..., channel], "F")
        resized_channels.append(
            np.asarray(plane.resize(size, Image.Resampling.LANCZOS), dtype=np.float32),
        )
    return from_premultiplied(np.stack(resized_channels, axis=2))


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA")).copy()
    rgba[..., :3][rgba[..., 3] == 0] = 0
    return Image.fromarray(rgba, "RGBA")


def round_ratio(numerator: int, denominator: int) -> int:
    """Round a positive rational using Python's ties-to-even rule without floats."""
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient % 2 == 1):
        quotient += 1
    return quotient


def resolve_high_resolution_dimensions(
    frame_width: int,
    frame_height: int,
) -> tuple[tuple[int, int], float]:
    if frame_width < 1 or frame_height < 1:
        raise ValueError("frame dimensions must be positive")
    if min(frame_width, frame_height) >= HIGH_RESOLUTION_SHORT_SIDE:
        raise ValueError("target frame shortest side must be smaller than 512px")
    if max(frame_width, frame_height) > MAX_TARGET_SIDE:
        raise ValueError(f"target frame longest side must not exceed {MAX_TARGET_SIDE}px")
    short_side = min(frame_width, frame_height)
    high_resolution_scale = HIGH_RESOLUTION_SHORT_SIDE / short_side
    high_resolution_size = (
        round_ratio(frame_width * HIGH_RESOLUTION_SHORT_SIDE, short_side),
        round_ratio(frame_height * HIGH_RESOLUTION_SHORT_SIDE, short_side),
    )
    if min(high_resolution_size) != HIGH_RESOLUTION_SHORT_SIDE:
        raise ValueError("high-resolution canvas shortest side must equal 512px")
    if max(high_resolution_size) > MAX_HIGH_RESOLUTION_SIDE:
        raise ValueError(
            f"high-resolution canvas longest side must not exceed {MAX_HIGH_RESOLUTION_SIDE}px",
        )
    return high_resolution_size, high_resolution_scale
