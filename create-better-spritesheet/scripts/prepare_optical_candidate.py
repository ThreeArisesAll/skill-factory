#!/usr/bin/env python3
"""Normalize one optical-size pre-master candidate and build opaque review comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from image_utils import (
    alpha_bbox,
    resize_premultiplied,
    resolve_frame_dimensions,
    resolve_master_dimensions,
)
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a high-resolution transparent optical-size candidate once.",
    )
    parser.add_argument("--source-alpha", required=True, type=Path, help="High-resolution RGBA candidate")
    parser.add_argument("--output-dir", required=True, type=Path, help="Fresh output directory")
    parser.add_argument("--name", default="character-optical", help="Output filename prefix")
    parser.add_argument("--original", type=Path, help="Optional original target-size RGBA frame")
    parser.add_argument("--sharpened", type=Path, help="Optional mildly sharpened target-size RGBA frame")
    parser.add_argument("--frame-size", type=int, help="Legacy shorthand for square frames")
    parser.add_argument("--frame-width", type=int)
    parser.add_argument("--frame-height", type=int)
    parser.add_argument(
        "--margin",
        type=float,
        required=True,
        help="Contract safe margin in final-size pixels",
    )
    parser.add_argument("--alpha-threshold", type=int, default=8, help="Alpha threshold used for visible bounds")
    parser.add_argument(
        "--key-rgb",
        type=int,
        nargs=3,
        metavar=("R", "G", "B"),
        help="Optional former chroma-key RGB used to report visible residuals",
    )
    parser.add_argument("--key-distance", type=float, default=30.0, help="RGB distance counted as key-like")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing named outputs")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[int, int]:
    frame_width, frame_height = resolve_frame_dimensions(
        args.frame_size,
        args.frame_width,
        args.frame_height,
    )
    resolve_master_dimensions(frame_width, frame_height)
    if args.margin < 2 or args.margin * 2 >= min(frame_width, frame_height):
        raise ValueError("--margin must leave a positive target-size content area")
    if not 0 <= args.alpha_threshold <= 254:
        raise ValueError("--alpha-threshold must be between 0 and 254")
    if args.key_rgb is not None and any(channel < 0 or channel > 255 for channel in args.key_rgb):
        raise ValueError("--key-rgb channels must be between 0 and 255")
    if args.key_distance < 0:
        raise ValueError("--key-distance must be non-negative")
    return frame_width, frame_height


def prepare_output(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def load_rgba(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode != "RGBA":
        raise ValueError(f"{path} must be RGBA, got {image.mode}")
    return image.copy()


def validate_source(image: Image.Image, threshold: int) -> tuple[int, int, int, int]:
    alpha = np.asarray(image.getchannel("A"))
    corner_alpha = int(alpha[[0, 0, -1, -1], [0, -1, 0, -1]].max())
    if corner_alpha > threshold:
        raise ValueError(f"source corners are not transparent: maximum alpha={corner_alpha}")
    bbox = alpha_bbox(image, threshold)
    left, top, right, bottom = bbox
    margins = (left, top, image.width - right, image.height - bottom)
    if min(margins) < 2:
        raise ValueError(
            "visible alpha touches the source border; remove the residual background before normalization",
        )
    return bbox


def normalize_candidate(
    source: Image.Image,
    bbox: tuple[int, int, int, int],
    working_size: tuple[int, int],
    margin_work: int,
) -> tuple[Image.Image, tuple[int, int]]:
    crop = source.crop(bbox)
    if source.width < working_size[0] // 2 or source.height < working_size[1] // 2:
        raise ValueError(
            "source canvas must be at least twice the target dimensions for optical sizing",
        )
    available_width = working_size[0] - margin_work * 2
    available_height = working_size[1] - margin_work * 2
    scale = min(available_width / crop.width, available_height / crop.height)
    fitted_size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    fitted = resize_premultiplied(crop, fitted_size)
    master = Image.new("RGBA", working_size, (0, 0, 0, 0))
    position = ((working_size[0] - fitted.width) // 2, (working_size[1] - fitted.height) // 2)
    master.alpha_composite(fitted, position)
    return master, fitted_size


def image_metrics(image: Image.Image, threshold: int, key_rgb: tuple[int, int, int] | None, key_distance: float) -> dict[str, object]:
    rgba = np.asarray(image.convert("RGBA"))
    alpha = rgba[..., 3]
    visible = alpha > threshold
    bbox = alpha_bbox(image, threshold)
    visible_pixels = int(np.count_nonzero(visible))
    partial_alpha = int(np.count_nonzero((alpha > 0) & (alpha < 255)))
    colors = int(len(np.unique(rgba[visible], axis=0)))
    transparent_rgb_max = int(rgba[..., :3][alpha == 0].max(initial=0))
    result: dict[str, object] = {
        "size": [image.width, image.height],
        "alpha_bbox": list(bbox),
        "alpha_bbox_size": [bbox[2] - bbox[0], bbox[3] - bbox[1]],
        "visible_pixels": visible_pixels,
        "visible_rgba_colors": colors,
        "partial_alpha_pixels": partial_alpha,
        "transparent_rgb_max": transparent_rgb_max,
    }
    if key_rgb is not None:
        rgb = rgba[..., :3].astype(np.float32)
        key = np.asarray(key_rgb, dtype=np.float32)
        distance = np.linalg.norm(rgb - key, axis=2)
        key_like = int(np.count_nonzero(visible & (distance <= key_distance)))
        result["key_rgb"] = list(key_rgb)
        result["key_like_visible_pixels"] = key_like
        result["key_like_visible_ratio"] = key_like / max(1, visible_pixels)
    return result


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    width, height = size
    pixels = np.full((height, width, 3), (224, 229, 232), dtype=np.uint8)
    yy, xx = np.indices((height, width))
    pixels[((xx // cell) + (yy // cell)) % 2 == 1] = (190, 198, 202)
    return Image.fromarray(pixels, "RGB")


def comparison(images: list[Image.Image], scale: int) -> Image.Image:
    gutter = 16
    rendered = [
        image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
        if scale > 1
        else image.copy()
        for image in images
    ]
    width = sum(image.width for image in rendered) + gutter * (len(rendered) - 1)
    height = max(image.height for image in rendered)
    canvas = checkerboard((width, height), cell=32).convert("RGBA")
    x = 0
    for image in rendered:
        canvas.alpha_composite(image, (x, 0))
        x += image.width + gutter
    return canvas.convert("RGB")


def main() -> int:
    args = parse_args()
    frame_width, frame_height = validate_args(args)
    prepare_output(args.output_dir, args.overwrite)

    source = load_rgba(args.source_alpha)
    source_bbox = validate_source(source, args.alpha_threshold)
    working_size, master_scale = resolve_master_dimensions(frame_width, frame_height)
    margin_work = round(args.margin * master_scale)
    master, fitted_size = normalize_candidate(source, source_bbox, working_size, margin_work)
    frame_size = (frame_width, frame_height)
    target_review = resize_premultiplied(master, frame_size)

    master_path = args.output_dir / f"{args.name}-pre-master-{working_size[0]}x{working_size[1]}.png"
    metrics_path = args.output_dir / f"{args.name}-metrics.json"
    master.save(master_path)

    key_rgb = tuple(args.key_rgb) if args.key_rgb is not None else None
    metrics = {
        "source": image_metrics(source, args.alpha_threshold, key_rgb, args.key_distance),
        "pre_master": image_metrics(master, args.alpha_threshold, key_rgb, args.key_distance),
        "target_review": image_metrics(target_review, args.alpha_threshold, key_rgb, args.key_distance),
        "master_scale": master_scale,
        "normalized_content_size": list(fitted_size),
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    controls: list[Image.Image] = []
    for label, path in (("original", args.original), ("sharpened", args.sharpened)):
        if path is None:
            continue
        image = load_rgba(path)
        if image.size != frame_size:
            raise ValueError(f"{label} frame is {image.size}; expected {frame_size}")
        controls.append(image)
    comparisons = controls + [target_review]
    if len(comparisons) > 1:
        comparison(comparisons, 1).save(args.output_dir / f"{args.name}-review-comparison-native.png")
        comparison(comparisons, 4).save(args.output_dir / f"{args.name}-review-comparison-4x.png")

    print(f"source bbox: {source_bbox} ({source_bbox[2] - source_bbox[0]}x{source_bbox[3] - source_bbox[1]})")
    print(
        f"normalized content: {fitted_size[0]}x{fitted_size[1]} "
        f"in {working_size[0]}x{working_size[1]}",
    )
    print(f"pre-master: {master_path}")
    print(f"target review bbox: {tuple(metrics['target_review']['alpha_bbox'])}")
    print(f"metrics: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
