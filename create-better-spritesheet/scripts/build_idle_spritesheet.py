#!/usr/bin/env python3
"""Build a closed high-fidelity idle loop from one transparent mother frame."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

from image_utils import alpha_bbox, from_premultiplied, resize_premultiplied, to_premultiplied


BASE_PHASES = np.array(
    [0.0, -0.25, -0.625, -1.0, -0.875, -0.55, -0.2, 0.1, 0.3, 0.2, 0.05, 0.0],
    dtype=np.float32,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a premultiplied-alpha idle sheet from one high-resolution RGBA mother frame.",
    )
    parser.add_argument("--master", required=True, type=Path, help="Transparent RGBA mother frame")
    parser.add_argument("--output-dir", required=True, type=Path, help="Fresh output directory")
    parser.add_argument("--name", default="character-idle", help="Output filename prefix")
    parser.add_argument("--frame-size", type=int, required=True, help="Final square frame size from the live asset contract")
    parser.add_argument(
        "--frame-count",
        type=int,
        required=True,
        help="Contract frame count including the repeated closing frame",
    )
    parser.add_argument("--working-scale", type=int, default=4, help="Working resolution multiplier")
    parser.add_argument(
        "--margin",
        type=float,
        required=True,
        help="Contract safe margin in final-size pixels",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        required=True,
        help="Contract peak head travel in final-size pixels",
    )
    parser.add_argument(
        "--loop-duration-ms",
        type=int,
        required=True,
        help="Contract preview loop duration",
    )
    parser.add_argument(
        "--sole-lock-ratio",
        type=float,
        default=0.93,
        help="Normalized content height where the locked sole-contact band begins",
    )
    parser.add_argument(
        "--fit-master",
        action="store_true",
        help="Fit a nonconforming source into the exact working canvas once",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing files with the same names in a non-empty output directory",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.frame_size < 32:
        raise ValueError("--frame-size must be at least 32")
    if args.frame_count < 4:
        raise ValueError("--frame-count must be at least 4")
    if args.working_scale < 2:
        raise ValueError("--working-scale must be at least 2")
    if not 0.85 <= args.sole_lock_ratio <= 0.98:
        raise ValueError("--sole-lock-ratio must be between 0.85 and 0.98")
    if args.margin < args.amplitude + 2:
        raise ValueError("--margin must exceed --amplitude by at least 2 pixels")
    if args.loop_duration_ms < args.frame_count:
        raise ValueError("--loop-duration-ms must be at least --frame-count")


def load_master(args: argparse.Namespace, working_size: int) -> Image.Image:
    source = Image.open(args.master).convert("RGBA")
    corner_alpha = np.asarray(source.getchannel("A"))[[0, 0, -1, -1], [0, -1, 0, -1]]
    if int(corner_alpha.max()) > 8:
        raise ValueError("mother frame corners are not transparent; remove the background first")

    if source.size == (working_size, working_size):
        master = source.copy()
    elif not args.fit_master:
        raise ValueError(
            f"mother frame is {source.width}x{source.height}; expected {working_size}x{working_size}. "
            "Use --fit-master to create the canonical working canvas once.",
        )
    else:
        left, top, right, bottom = alpha_bbox(source)
        crop = source.crop((left, top, right, bottom))
        if max(crop.size) < args.frame_size * 2:
            raise ValueError("source is too small for a high-fidelity mother frame; regenerate it at high resolution")
        margin = int(round(args.margin * args.working_scale))
        available = working_size - margin * 2
        scale = min(available / crop.width, available / crop.height)
        fitted_size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
        fitted = resize_premultiplied(crop, fitted_size)
        master = Image.new("RGBA", (working_size, working_size), (0, 0, 0, 0))
        position = ((working_size - fitted.width) // 2, (working_size - fitted.height) // 2)
        master.alpha_composite(fitted, position)

    left, top, right, bottom = alpha_bbox(master)
    margin_work = int(round(args.margin * args.working_scale))
    if min(left, top, working_size - right, working_size - bottom) < margin_work - 2:
        raise ValueError("canonical mother frame does not meet the requested safe margin")
    return master


def phase_curve(frame_count: int) -> np.ndarray:
    source_x = np.linspace(0.0, 1.0, len(BASE_PHASES), dtype=np.float32)
    target_x = np.linspace(0.0, 1.0, frame_count, dtype=np.float32)
    phases = np.interp(target_x, source_x, BASE_PHASES).astype(np.float32)
    phases[0] = 0.0
    phases[-1] = 0.0
    return phases


def vertical_weight(normalized_y: np.ndarray, sole_lock_ratio: float) -> np.ndarray:
    controls = np.array([0.0, 0.48, 0.65, 0.80, 0.88, sole_lock_ratio, 1.0], dtype=np.float32)
    weights = np.array([1.0, 1.0, 0.82, 0.55, 0.28, 0.0, 0.0], dtype=np.float32)
    return np.interp(np.clip(normalized_y, 0.0, 1.0), controls, weights).astype(np.float32)


def lateral_weight(normalized_y: np.ndarray, sole_lock_ratio: float) -> np.ndarray:
    controls = np.array([0.0, 0.52, 0.66, 0.78, 0.89, sole_lock_ratio, 1.0], dtype=np.float32)
    weights = np.array([0.0, 0.0, 0.35, 1.0, 0.25, 0.0, 0.0], dtype=np.float32)
    return np.interp(np.clip(normalized_y, 0.0, 1.0), controls, weights).astype(np.float32)


def bilinear_sample(array: np.ndarray, source_x: np.ndarray, source_y: np.ndarray) -> np.ndarray:
    height, width, _ = array.shape
    x = np.clip(source_x, 0.0, width - 1.0)
    y = np.clip(source_y, 0.0, height - 1.0)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    wx = (x - x0)[..., None]
    wy = (y - y0)[..., None]
    top = array[y0, x0] * (1.0 - wx) + array[y0, x1] * wx
    bottom = array[y1, x0] * (1.0 - wx) + array[y1, x1] * wx
    return top * (1.0 - wy) + bottom * wy


def render_frame(
    master: Image.Image,
    bbox: tuple[int, int, int, int],
    phase: float,
    amplitude_work: float,
    sole_lock_ratio: float,
) -> Image.Image:
    source = to_premultiplied(master)
    height, width, _ = source.shape
    left, top, right, bottom = bbox
    content_height = max(1.0, float(bottom - top))
    target_y = np.arange(height, dtype=np.float32)[:, None]
    source_y = target_y.copy()
    offset = phase * amplitude_work

    for _ in range(5):
        normalized_y = (source_y - top) / content_height
        weight = vertical_weight(normalized_y, sole_lock_ratio)
        inside = (source_y >= top) & (source_y < bottom)
        source_y = np.where(inside, target_y - offset * weight, target_y)

    normalized_y = (source_y - top) / content_height
    stance = 1.0 + (-phase * 0.012) * lateral_weight(normalized_y, sole_lock_ratio)
    target_x = np.arange(width, dtype=np.float32)[None, :]
    center_x = (left + right - 1) / 2.0
    source_x = center_x + (target_x - center_x) / stance
    source_y_full = np.broadcast_to(source_y, source_x.shape)
    warped = bilinear_sample(source, source_x, source_y_full)

    lock_start = int(math.ceil(top + content_height * sole_lock_ratio))
    warped[lock_start:, :, :] = source[lock_start:, :, :]
    return from_premultiplied(warped)


def prepare_output(output_dir: Path, overwrite: bool) -> tuple[Path, Path]:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    high_frames = output_dir / "high-frames"
    final_frames = output_dir / "frames"
    high_frames.mkdir(exist_ok=True)
    final_frames.mkdir(exist_ok=True)
    return high_frames, final_frames


def frame_durations(loop_duration_ms: int, frame_count: int) -> list[int]:
    duration_ms, remainder = divmod(loop_duration_ms, frame_count)
    return [duration_ms + (index < remainder) for index in range(frame_count)]


def save_animation(frames: list[Image.Image], output_dir: Path, name: str, loop_duration_ms: int) -> None:
    durations = frame_durations(loop_duration_ms, len(frames))
    frames[0].save(
        output_dir / f"{name}.apng.png",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=0,
        blend=0,
        optimize=False,
    )
    frames[0].save(
        output_dir / f"{name}.webp",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        method=6,
    )
    review_size = (frames[0].width * 4, frames[0].height * 4)
    checker = Image.new("RGB", review_size, (224, 229, 232))
    checker_pixels = np.asarray(checker).copy()
    cell = 32
    yy, xx = np.indices((review_size[1], review_size[0]))
    dark = ((xx // cell) + (yy // cell)) % 2 == 1
    checker_pixels[dark] = (190, 198, 202)
    checker = Image.fromarray(checker_pixels, "RGB")
    review_frames = []
    for frame in frames:
        enlarged = frame.resize(review_size, Image.Resampling.LANCZOS)
        review = checker.convert("RGBA")
        review.alpha_composite(enlarged)
        review_frames.append(review.convert("RGB"))
    review_frames[0].save(
        output_dir / f"{name}-review-4x.webp",
        save_all=True,
        append_images=review_frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        method=6,
    )


def main() -> int:
    args = parse_args()
    validate_args(args)
    working_size = args.frame_size * args.working_scale
    master = load_master(args, working_size)
    high_dir, final_dir = prepare_output(args.output_dir, args.overwrite)
    master_path = args.output_dir / f"{args.name}-master-{working_size}.png"
    master.save(master_path)
    bbox = alpha_bbox(master)
    phases = phase_curve(args.frame_count)
    high_frames: list[Image.Image] = []
    final_frames: list[Image.Image] = []

    for index, phase in enumerate(phases, start=1):
        high_frame = render_frame(
            master,
            bbox,
            float(phase),
            args.amplitude * args.working_scale,
            args.sole_lock_ratio,
        )
        final_frame = resize_premultiplied(high_frame, (args.frame_size, args.frame_size))
        high_frame.save(high_dir / f"{index:02d}.png")
        final_frame.save(final_dir / f"{index:02d}.png")
        high_frames.append(high_frame)
        final_frames.append(final_frame)

    sheet = Image.new("RGBA", (args.frame_size * args.frame_count, args.frame_size), (0, 0, 0, 0))
    for index, frame in enumerate(final_frames):
        sheet.alpha_composite(frame, (index * args.frame_size, 0))
    sheet_path = args.output_dir / f"{args.name}-{args.frame_count}f-{args.frame_size}x{args.frame_size}-sheet.png"
    sheet.save(sheet_path)
    save_animation(final_frames, args.output_dir, args.name, args.loop_duration_ms)

    print(f"mother: {master_path}")
    print(f"sheet: {sheet_path} ({sheet.width}x{sheet.height}, RGBA)")
    print(f"frames: {len(final_frames)} at {args.frame_size}x{args.frame_size}")
    print(f"preview duration: {args.loop_duration_ms} ms per loop")
    print(f"loop: frame 1 == frame {args.frame_count}: {np.array_equal(np.asarray(final_frames[0]), np.asarray(final_frames[-1]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
