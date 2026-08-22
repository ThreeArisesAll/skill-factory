"""Bounded PNG decoding and deterministic premultiplied-alpha rendering."""

from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .errors import ContractError
from .package_io import RegularFileSnapshot, ResourceBudget, read_regular_file_snapshot
from .protocol import (
    ALPHA_BOUNDARY_CHECK,
    HIGH_RESOLUTION_SHORT_SIDE,
    IDENTITY_ALGORITHM,
    LOW_ALPHA_BOUNDARY_THRESHOLD,
    MASK_POLICY,
    OUTLINE_ALGORITHM,
    OUTLINE_ALPHA_THRESHOLD,
    PIXEL_PROTOCOL_ID,
    RENDERING_PIPELINE,
    RENDERING_RECEIPT_SCHEMA,
    SAMPLER,
)

MAX_HIGH_RESOLUTION_SIDE = 16384
MAX_TARGET_SIDE = 4096
MAX_PNG_FILE_BYTES = 64 * 1024 * 1024
MAX_PNG_DECODED_PIXELS = 64 * 1024 * 1024
MAX_OUTLINE_CANVAS_PIXELS = HIGH_RESOLUTION_SHORT_SIDE * MAX_HIGH_RESOLUTION_SIDE
REVIEW_BACKGROUNDS = {
    "white": (255, 255, 255, 255),
    "dark": (24, 24, 24, 255),
}


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


def normalize_low_alpha(
    image: Image.Image,
    threshold: int = LOW_ALPHA_BOUNDARY_THRESHOLD,
) -> Image.Image:
    if not 0 <= threshold < 255:
        raise ContractError("low-alpha normalization threshold must be between 0 and 254")
    rgba = np.asarray(image.convert("RGBA")).copy()
    rgba[rgba[..., 3] <= threshold] = 0
    return Image.fromarray(rgba, "RGBA")


def _exterior_partial_alpha_mask(image: Image.Image) -> np.ndarray:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    transparent = alpha == 0
    adjacent = np.zeros(alpha.shape, dtype=bool)
    height, width = alpha.shape
    for dy, dx in (
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1), (0, 1),
        (1, -1), (1, 0), (1, 1),
    ):
        source_y = slice(max(0, -dy), min(height, height - dy))
        source_x = slice(max(0, -dx), min(width, width - dx))
        target_y = slice(max(0, dy), min(height, height + dy))
        target_x = slice(max(0, dx), min(width, width + dx))
        adjacent[target_y, target_x] |= transparent[source_y, source_x]
    return (alpha > 0) & (alpha < 255) & adjacent


def alpha_policy_record(
    source: Image.Image,
    candidate: Image.Image,
    outline_enabled: bool,
) -> dict[str, object]:
    source_boundary = _exterior_partial_alpha_mask(source)
    source_alpha = np.asarray(source.getchannel("A"), dtype=np.uint8)
    normalized_source = normalize_low_alpha(source)
    surviving_boundary = _exterior_partial_alpha_mask(normalized_source)
    unbacked_count = 0
    if outline_enabled:
        candidate_alpha = np.asarray(candidate.getchannel("A"), dtype=np.uint8)
        unbacked_count = int(
            np.count_nonzero(
                surviving_boundary & (candidate_alpha != OUTLINE_ALPHA_THRESHOLD),
            ),
        )
    return {
        "boundary_check": ALPHA_BOUNDARY_CHECK,
        "low_alpha_threshold": LOW_ALPHA_BOUNDARY_THRESHOLD,
        "outline_mask": MASK_POLICY,
        "outline_alpha_threshold": OUTLINE_ALPHA_THRESHOLD,
        "source_low_alpha_boundary_pixels": int(
            np.count_nonzero(
                source_boundary & (source_alpha <= LOW_ALPHA_BOUNDARY_THRESHOLD),
            ),
        ),
        "source_partial_alpha_boundary_pixels": int(np.count_nonzero(source_boundary)),
        "unbacked_source_boundary_pixels": unbacked_count,
        "status": "passed" if unbacked_count == 0 else "failed",
    }


def _checkerboard(size: tuple[int, int], tile: int) -> Image.Image:
    width, height = size
    x_parity = ((np.arange(width, dtype=np.uint32) // tile) & 1).astype(np.uint8)
    y_parity = ((np.arange(height, dtype=np.uint32) // tile) & 1).astype(np.uint8)
    squares = np.bitwise_xor(y_parity[:, None], x_parity[None, :])
    luminance = np.take(np.array((216, 160), dtype=np.uint8), squares)
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = luminance[..., None]
    rgba[..., 3] = 255
    return Image.fromarray(rgba, "RGBA")


def _preview_png(image: Image.Image) -> bytes:
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def review_preview_payloads(
    candidate: Image.Image,
    target_size: tuple[int, int],
) -> list[tuple[dict[str, object], bytes]]:
    scales = (
        ("high-resolution", candidate),
        ("native", resize_premultiplied(candidate, target_size)),
    )
    records: list[tuple[dict[str, object], bytes]] = []
    for scale, sprite in scales:
        tile = max(1, min(sprite.size) // 16)
        backgrounds = {
            **{
                name: Image.new("RGBA", sprite.size, color)
                for name, color in REVIEW_BACKGROUNDS.items()
            },
            "checkerboard": _checkerboard(sprite.size, tile),
        }
        for background_name, background in backgrounds.items():
            preview = Image.alpha_composite(background, sprite)
            png_bytes = _preview_png(preview)
            path = f"review/{scale}-{background_name}.png"
            records.append(({
                "scale": scale,
                "background": background_name,
                "path": path,
                "sha256": hashlib.sha256(png_bytes).hexdigest(),
                "rgba_sha256": hashlib.sha256(preview.tobytes()).hexdigest(),
                "width": preview.width,
                "height": preview.height,
                "mode": preview.mode,
            }, png_bytes))
    return records


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
def decode_rgba(
    data: bytes,
    location: str,
    *,
    expected_size: tuple[int, int] | None = None,
    budget: ResourceBudget | None = None,
) -> Image.Image:
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
            if expected_size is not None and opened.size != expected_size:
                raise ContractError(
                    f"{location} dimensions must equal {expected_size[0]}x{expected_size[1]}",
                )
            if budget is not None:
                budget.consume_decoded_pixels(opened.width * opened.height, location)
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
    image = decode_rgba(snapshot.data, location, budget=budget)
    return image, snapshot


def normalize_to_canvas(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = min(size[0] / source.width, size[1] / source.height)
    fitted_size = (max(1, round(source.width * ratio)), max(1, round(source.height * ratio)))
    fitted = resize_premultiplied(source, fitted_size)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return clear_transparent_rgb(canvas)


def _integer_squared_distance_transform(seed: np.ndarray) -> np.ndarray:
    """Return exact squared center distances to the nearest true pixel."""
    height, width = seed.shape
    if height == 0 or width == 0:
        return np.empty(seed.shape, dtype=np.int64)

    # Orient the work so the Python lower-envelope pass has the fewest rows.
    oriented = seed if height <= width else seed.T
    short_side, long_side = oriented.shape
    infinity = np.iinfo(np.int64).max // 4

    distances = np.empty((short_side, long_side), dtype=np.int64)
    last_seed = np.full(long_side, -short_side - 1, dtype=np.int64)
    for coordinate in range(short_side):
        last_seed = np.where(oriented[coordinate], coordinate, last_seed)
        delta = coordinate - last_seed
        distances[coordinate] = delta * delta

    next_seed = np.full(long_side, short_side * 2 + 1, dtype=np.int64)
    for coordinate in range(short_side - 1, -1, -1):
        next_seed = np.where(oriented[coordinate], coordinate, next_seed)
        delta = next_seed - coordinate
        distances[coordinate] = np.minimum(distances[coordinate], delta * delta)

    distances[:, ~np.any(oriented, axis=0)] = infinity
    positions = np.empty(long_side, dtype=np.int64)
    starts = np.empty(long_side, dtype=np.int64)
    transformed = np.empty(long_side, dtype=np.int64)

    for row_index in range(short_side):
        values = distances[row_index]
        envelope_size = 0
        for candidate in range(long_side):
            candidate_value = int(values[candidate])
            if candidate_value == infinity:
                continue
            start = 0
            while envelope_size:
                previous = int(positions[envelope_size - 1])
                numerator = (
                    candidate * candidate
                    + candidate_value
                    - previous * previous
                    - int(values[previous])
                )
                denominator = 2 * (candidate - previous)
                start = -(-numerator // denominator)
                if start > int(starts[envelope_size - 1]):
                    break
                envelope_size -= 1
            if envelope_size == 0:
                start = 0
            if start >= long_side:
                continue
            positions[envelope_size] = candidate
            starts[envelope_size] = max(0, start)
            envelope_size += 1

        if envelope_size == 0:
            transformed.fill(infinity)
        else:
            envelope_index = 0
            for coordinate in range(long_side):
                while (
                    envelope_index + 1 < envelope_size
                    and int(starts[envelope_index + 1]) <= coordinate
                ):
                    envelope_index += 1
                nearest = int(positions[envelope_index])
                delta = coordinate - nearest
                transformed[coordinate] = delta * delta + int(values[nearest])
        distances[row_index] = transformed

    return distances if height <= width else distances.T


def _euclidean_outline_coverage(seed: np.ndarray, radius: int) -> np.ndarray:
    """Build an opaque Euclidean inner band plus one-pixel coverage ramp."""
    if radius < 1 or radius >= HIGH_RESOLUTION_SHORT_SIDE:
        raise ContractError(
            f"resolved outline width must be between 1 and {HIGH_RESOLUTION_SHORT_SIDE - 1}px",
        )
    if not np.any(seed):
        return np.zeros(seed.shape, dtype=np.uint8)

    occupied_y = np.flatnonzero(np.any(seed, axis=1))
    occupied_x = np.flatnonzero(np.any(seed, axis=0))
    outer_radius = radius + 1
    left = max(0, int(occupied_x[0]) - outer_radius)
    top = max(0, int(occupied_y[0]) - outer_radius)
    right = min(seed.shape[1], int(occupied_x[-1]) + outer_radius + 1)
    bottom = min(seed.shape[0], int(occupied_y[-1]) + outer_radius + 1)
    cropped_seed = seed[top:bottom, left:right]
    squared_distance = _integer_squared_distance_transform(cropped_seed)

    inner_squared = radius * radius
    outer_squared = outer_radius * outer_radius
    lookup = np.zeros(outer_squared + 1, dtype=np.uint8)
    lookup[: inner_squared + 1] = 255
    fixed_one = 1 << 16
    fixed_outer_radius = outer_radius * fixed_one
    for distance_squared in range(inner_squared + 1, outer_squared):
        fixed_distance = math.isqrt(distance_squared << 32)
        remaining = fixed_outer_radius - fixed_distance
        lookup[distance_squared] = round_ratio(remaining * 255, fixed_one)

    cropped_coverage = np.zeros(cropped_seed.shape, dtype=np.uint8)
    inside = squared_distance <= outer_squared
    cropped_coverage[inside] = lookup[squared_distance[inside]]
    cropped_coverage[cropped_seed] = 0
    coverage = np.zeros(seed.shape, dtype=np.uint8)
    coverage[top:bottom, left:right] = cropped_coverage
    return coverage


def apply_outline(
    image: Image.Image,
    target_width: int,
    target_short_side: int,
    color: list[Any],
    *,
    alpha_threshold: int = OUTLINE_ALPHA_THRESHOLD,
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
    if color[3] == 0:
        raise ContractError(
            "outline.color alpha must be greater than zero; "
            "enabled outline color alpha must be 255",
        )
    if color[3] != 255:
        raise ContractError("outline.color alpha must be 255")
    if (
        not isinstance(target_width, int)
        or isinstance(target_width, bool)
        or target_width < 1
        or not isinstance(target_short_side, int)
        or isinstance(target_short_side, bool)
        or target_short_side < 1
    ):
        raise ContractError("outline width and target shortest side must be positive integers")
    resolved_width = max(
        1,
        round_ratio(target_width * HIGH_RESOLUTION_SHORT_SIDE, target_short_side),
    )
    if alpha_threshold != OUTLINE_ALPHA_THRESHOLD:
        raise ContractError(f"outline alpha threshold must equal {OUTLINE_ALPHA_THRESHOLD}")
    if image.width * image.height > MAX_OUTLINE_CANVAS_PIXELS:
        raise ContractError(
            f"outline canvas must not exceed {MAX_OUTLINE_CANVAS_PIXELS} pixels",
        )
    alpha = np.asarray(image.convert("RGBA"))[..., 3]
    silhouette_seed = alpha == OUTLINE_ALPHA_THRESHOLD
    if not np.any(silhouette_seed):
        raise ContractError("enabled outline requires an opaque silhouette seed")
    coverage = _euclidean_outline_coverage(silhouette_seed, resolved_width)
    ring = Image.fromarray(coverage, "L")
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
        "pixel_protocol_id": PIXEL_PROTOCOL_ID,
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
