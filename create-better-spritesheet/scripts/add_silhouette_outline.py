#!/usr/bin/env python3
"""Create an outlined canonical master from one working-size RGBA source."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from image_utils import (
    alpha_bbox,
    clear_transparent_rgb,
    resize_premultiplied,
    resolve_frame_dimensions,
    resolve_master_dimensions,
)
from PIL import Image, ImageFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a deterministic outer silhouette outline without re-inking the character.",
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Fixed-size high-resolution RGBA pre-master source",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="Fresh output directory")
    parser.add_argument("--name", default="character-outline", help="Output filename prefix")
    parser.add_argument("--frame-size", type=int, help="Legacy shorthand for square frames")
    parser.add_argument("--frame-width", type=int)
    parser.add_argument("--frame-height", type=int)
    parser.add_argument(
        "--outline-radius",
        type=int,
        required=True,
        help="Contract outline radius in canonical-master pixels",
    )
    parser.add_argument(
        "--outline-color",
        required=True,
        help="Contract outline color as #RRGGBB",
    )
    parser.add_argument(
        "--safe-margin",
        type=int,
        required=True,
        help="Required final-size safe margin from the live asset contract",
    )
    parser.add_argument("--alpha-threshold", type=int, default=8, help="Alpha threshold used for visible bounds")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing named outputs")
    return parser.parse_args()


def parse_hex_color(value: str) -> tuple[int, int, int]:
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value) is None:
        raise ValueError("--outline-color must use #RRGGBB")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def validate_args(args: argparse.Namespace) -> tuple[int, int]:
    frame_width, frame_height = resolve_frame_dimensions(
        args.frame_size,
        args.frame_width,
        args.frame_height,
    )
    resolve_master_dimensions(frame_width, frame_height)
    if args.outline_radius < 1:
        raise ValueError("--outline-radius must be positive")
    if args.safe_margin < 1:
        raise ValueError("--safe-margin must be positive")
    if not 0 <= args.alpha_threshold <= 254:
        raise ValueError("--alpha-threshold must be between 0 and 254")
    parse_hex_color(args.outline_color)
    return frame_width, frame_height


def prepare_output(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def load_source(path: Path, expected_size: tuple[int, int], threshold: int) -> Image.Image:
    image = Image.open(path)
    if image.mode != "RGBA":
        raise ValueError(f"pre-master source must be RGBA, got {image.mode}")
    if image.size != expected_size:
        raise ValueError(
            f"pre-master source is {image.width}x{image.height}; "
            f"expected {expected_size[0]}x{expected_size[1]}",
        )
    alpha = np.asarray(image.getchannel("A"))
    corner_alpha = int(alpha[[0, 0, -1, -1], [0, -1, 0, -1]].max())
    if corner_alpha > threshold:
        raise ValueError(
            f"pre-master source corners are not transparent: maximum alpha={corner_alpha}",
        )
    alpha_bbox(image, threshold)
    return image.copy()


def add_outline(source: Image.Image, radius: int, color: tuple[int, int, int]) -> Image.Image:
    dilated_alpha = source.getchannel("A").filter(ImageFilter.MaxFilter(radius * 2 + 1))
    stroke = Image.new("RGBA", source.size, (*color, 0))
    stroke.putalpha(dilated_alpha)
    return Image.alpha_composite(stroke, source)


def transparent_rgb_max(image: Image.Image) -> int:
    rgba = np.asarray(image)
    return int(rgba[..., :3][rgba[..., 3] == 0].max(initial=0))


def minimum_margin(bbox: tuple[int, int, int, int], size: tuple[int, int]) -> int:
    left, top, right, bottom = bbox
    width, height = size
    return min(left, top, width - right, height - bottom)


def checkerboard(size: tuple[int, int], cell: int = 32) -> Image.Image:
    width, height = size
    pixels = np.full((height, width, 3), (224, 229, 232), dtype=np.uint8)
    yy, xx = np.indices((height, width))
    pixels[((xx // cell) + (yy // cell)) % 2 == 1] = (190, 198, 202)
    return Image.fromarray(pixels, "RGB")


def comparison(original: Image.Image, outlined: Image.Image, scale: int) -> Image.Image:
    gutter = 16
    if scale > 1:
        size = (original.width * scale, original.height * scale)
        original = original.resize(size, Image.Resampling.LANCZOS)
        outlined = outlined.resize(size, Image.Resampling.LANCZOS)
    output_size = (original.width * 2 + gutter, original.height)
    canvas = checkerboard(output_size).convert("RGBA")
    canvas.alpha_composite(original, (0, 0))
    canvas.alpha_composite(outlined, (original.width + gutter, 0))
    return canvas.convert("RGB")


def main() -> int:
    args = parse_args()
    frame_width, frame_height = validate_args(args)
    prepare_output(args.output_dir, args.overwrite)

    working_size, master_scale = resolve_master_dimensions(frame_width, frame_height)
    source = load_source(args.source, working_size, args.alpha_threshold)
    color = parse_hex_color(args.outline_color)
    outlined_master = clear_transparent_rgb(add_outline(source, args.outline_radius, color))
    frame_size = (frame_width, frame_height)
    original_frame = resize_premultiplied(source, frame_size)
    outlined_frame = clear_transparent_rgb(
        resize_premultiplied(outlined_master, frame_size),
    )

    master_bbox = alpha_bbox(source, args.alpha_threshold)
    outlined_master_bbox = alpha_bbox(outlined_master, args.alpha_threshold)
    frame_bbox = alpha_bbox(outlined_frame, args.alpha_threshold)
    margin = minimum_margin(frame_bbox, frame_size)
    if margin < args.safe_margin:
        raise ValueError(f"outlined target frame margin is {margin}px; required={args.safe_margin}px")

    master_rgba = np.asarray(source)
    outlined_rgba = np.asarray(outlined_master)
    opaque = master_rgba[..., 3] == 255
    interior_equal = bool(np.array_equal(master_rgba[opaque], outlined_rgba[opaque]))
    if not interior_equal:
        raise ValueError("opaque interior pixels changed while adding the outline")
    if transparent_rgb_max(outlined_master) != 0 or transparent_rgb_max(outlined_frame) != 0:
        raise ValueError("outline output contains RGB contamination under alpha=0")

    master_path = args.output_dir / f"{args.name}-canonical-master-{working_size[0]}x{working_size[1]}.png"
    metrics_path = args.output_dir / f"{args.name}-metrics.json"
    outlined_master.save(master_path)
    comparison(original_frame, outlined_frame, 1).save(
        args.output_dir / f"{args.name}-review-comparison-native.png",
    )
    comparison(original_frame, outlined_frame, 4).save(
        args.output_dir / f"{args.name}-review-comparison-4x.png",
    )

    metrics = {
        "working_size": list(working_size),
        "frame_size": list(frame_size),
        "outline_radius_working_pixels": args.outline_radius,
        "master_scale": master_scale,
        "outline_radius_target_pixels": args.outline_radius / master_scale,
        "outline_color": args.outline_color.lower(),
        "original_master_bbox": list(master_bbox),
        "outlined_master_bbox": list(outlined_master_bbox),
        "outlined_target_review_bbox": list(frame_bbox),
        "minimum_target_margin": margin,
        "opaque_interior_pixel_identical": interior_equal,
        "transparent_rgb_max": 0,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    print(f"master: {master_path}")
    print(
        f"outline: {args.outline_radius}px at {working_size[0]}x{working_size[1]}, "
        f"{args.outline_radius / master_scale:.2f}px at target",
    )
    print(f"bboxes: original={master_bbox}, outlined={outlined_master_bbox}, target={frame_bbox}")
    print(f"minimum target margin: {margin}px")
    print(f"opaque interior pixel-identical: {interior_equal}")
    print(f"metrics: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
