"""Bounded PNG decoding and deterministic premultiplied-alpha rendering."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from .errors import ContractError
from .package_io import RegularFileSnapshot, ResourceBudget, read_regular_file_snapshot
from .protocol import (
    HIGH_RESOLUTION_SHORT_SIDE,
    IDENTITY_ALGORITHM,
    MASK_POLICY,
    OUTLINE_ALGORITHM,
    RENDERING_PIPELINE,
    RENDERING_RECEIPT_SCHEMA,
    SAMPLER,
)

MAX_HIGH_RESOLUTION_SIDE = 16384
MAX_TARGET_SIDE = 4096
MAX_PNG_FILE_BYTES = 64 * 1024 * 1024
MAX_PNG_DECODED_PIXELS = 64 * 1024 * 1024
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
def decode_rgba(data: bytes, location: str) -> Image.Image:
    if len(data) > MAX_PNG_FILE_BYTES:
        raise ContractError(f"{location} PNG file exceeds {MAX_PNG_FILE_BYTES} bytes")
    try:
        with Image.open(io.BytesIO(data)) as opened:
            if opened.format != "PNG":
                raise ContractError(f"{location} must use the PNG container")
            if opened.mode != "RGBA":
                raise ContractError(f"{location} must be RGBA")
            if opened.width * opened.height > MAX_PNG_DECODED_PIXELS:
                raise ContractError(
                    f"{location} decoded image exceeds {MAX_PNG_DECODED_PIXELS} pixels",
                )
            opened.load()
            return opened.copy()
    except (OSError, Image.DecompressionBombError) as error:
        raise ContractError(f"cannot decode {location}: {error}") from error


def open_rgba(path: Path, location: str) -> Image.Image:
    image, _ = open_rgba_snapshot(path, location)
    return image


def open_rgba_snapshot(
    path: Path,
    location: str,
    *,
    budget: ResourceBudget | None = None,
) -> tuple[Image.Image, RegularFileSnapshot]:
    snapshot = read_regular_file_snapshot(
        path,
        location,
        MAX_PNG_FILE_BYTES,
        budget=budget,
    )
    image = decode_rgba(snapshot.data, location)
    if budget is not None:
        budget.consume_decoded_pixels(image.width * image.height, location)
    return image, snapshot


def normalize_to_canvas(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = min(size[0] / source.width, size[1] / source.height)
    fitted_size = (max(1, round(source.width * ratio)), max(1, round(source.height * ratio)))
    fitted = resize_premultiplied(source, fitted_size)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return clear_transparent_rgb(canvas)


def apply_outline(
    image: Image.Image,
    target_width: int,
    target_short_side: int,
    color: list[Any],
) -> tuple[Image.Image, int]:
    if (
        len(color) != 4
        or any(
            not isinstance(channel, int)
            or isinstance(channel, bool)
            or not 0 <= channel <= 255
            for channel in color
        )
    ):
        raise ContractError("outline.color must contain four integers between 0 and 255")
    resolved_width = max(
        1,
        round(target_width * HIGH_RESOLUTION_SHORT_SIDE / target_short_side),
    )
    alpha = image.getchannel("A")
    silhouette = alpha.point(lambda value: 255 if value > 0 else 0)
    expanded = silhouette.filter(ImageFilter.MaxFilter(resolved_width * 2 + 1))
    ring = ImageChops.subtract(expanded, silhouette)
    if color[3] != 255:
        ring = ring.point(lambda value: round(value * color[3] / 255))
    outlined = Image.new("RGBA", image.size, tuple(color))
    outlined.putalpha(ring)
    outlined.alpha_composite(image)
    return clear_transparent_rgb(outlined), resolved_width


def render_high_resolution_source(
    source: Image.Image,
    outline: dict[str, Any],
    target_size: tuple[int, int],
) -> tuple[Image.Image, Image.Image, int]:
    alpha = source.getchannel("A")
    if alpha.getbbox() is None:
        raise ContractError("high-resolution frame source must contain nonzero alpha")
    if outline["enabled"]:
        outlined, resolved_width = apply_outline(
            source,
            outline["target_width"],
            min(target_size),
            outline["color"],
        )
    else:
        outlined = clear_transparent_rgb(source)
        resolved_width = 0
    outlined_alpha = outlined.getchannel("A")
    width, height = outlined.size
    touches_border = (
        outlined_alpha.crop((0, 0, width, 1)).getbbox() is not None
        or outlined_alpha.crop((0, height - 1, width, height)).getbbox() is not None
        or outlined_alpha.crop((0, 0, 1, height)).getbbox() is not None
        or outlined_alpha.crop((width - 1, 0, width, height)).getbbox() is not None
    )
    if touches_border:
        raise ContractError("rendered high-resolution frame must not touch the canvas border")
    cell = resize_premultiplied(outlined, target_size)
    return outlined, cell, resolved_width



def rendering_frame_record(
    source: str,
    source_sha256: str | None,
    outlined: Image.Image,
    cell: Image.Image,
) -> dict[str, Any]:
    """Construct one rendering receipt frame through the shared protocol path."""
    return {
        "source": source,
        "source_sha256": source_sha256,
        "outlined_rgba_sha256": hashlib.sha256(outlined.tobytes()).hexdigest(),
        "cell_rgba_sha256": hashlib.sha256(cell.tobytes()).hexdigest(),
    }


def rendering_receipt(
    outline: dict[str, Any] | None,
    resolved_outline_width: int,
    frames: list[dict[str, Any]],
    sheet_rgba_sha256: str | None,
) -> dict[str, Any]:
    """Construct a complete receipt for both package creation and verification."""
    return {
        "schema_version": RENDERING_RECEIPT_SCHEMA,
        "pipeline": RENDERING_PIPELINE,
        "mask_policy": MASK_POLICY,
        "outline_algorithm": (
            OUTLINE_ALGORITHM if isinstance(outline, dict) and outline.get("enabled")
            else IDENTITY_ALGORITHM
        ),
        "sampler": SAMPLER,
        "resolved_high_resolution_outline_width": resolved_outline_width,
        "frames": frames,
        "sheet_rgba_sha256": sheet_rgba_sha256,
    }
