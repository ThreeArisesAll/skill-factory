#!/usr/bin/env python3
"""Shared premultiplied-alpha image helpers for spritesheet tools."""

from __future__ import annotations

import numpy as np
from PIL import Image

MASTER_SHORT_SIDE = 512


def alpha_bbox(image: Image.Image, threshold: int = 8) -> tuple[int, int, int, int]:
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > threshold)
    if len(xs) == 0:
        raise ValueError("image has no visible pixels")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


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


def resolve_frame_dimensions(
    frame_size: int | None,
    frame_width: int | None,
    frame_height: int | None,
) -> tuple[int, int]:
    if frame_size is not None:
        if frame_width is not None or frame_height is not None:
            raise ValueError("use --frame-size or --frame-width/--frame-height, not both")
        frame_width = frame_height = frame_size
    if frame_width is None or frame_height is None:
        raise ValueError("provide --frame-width and --frame-height")
    if frame_width < 1 or frame_height < 1:
        raise ValueError("frame dimensions must be positive")
    return frame_width, frame_height


def resolve_master_dimensions(
    frame_width: int,
    frame_height: int,
) -> tuple[tuple[int, int], float]:
    if frame_width < 1 or frame_height < 1:
        raise ValueError("frame dimensions must be positive")
    master_scale = MASTER_SHORT_SIDE / min(frame_width, frame_height)
    master_size = (
        round(frame_width * master_scale),
        round(frame_height * master_scale),
    )
    if min(master_size) != MASTER_SHORT_SIDE:
        raise ValueError("canonical master shortest side must equal 512px")
    return master_size, master_scale
