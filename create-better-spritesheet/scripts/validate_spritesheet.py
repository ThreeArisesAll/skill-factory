#!/usr/bin/env python3
"""Validate spritesheet layout, alpha integrity, loops, and motion contracts."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from image_utils import resolve_frame_dimensions


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an RGBA spritesheet grid.")
    parser.add_argument("--sheet", required=True, type=Path)
    parser.add_argument("--frame-size", type=int, help="Legacy shorthand for square frames")
    parser.add_argument("--frame-width", type=int)
    parser.add_argument("--frame-height", type=int)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--columns", type=int, help="Defaults to frame count for a horizontal strip")
    parser.add_argument("--order", choices=("row-major", "column-major"), default="row-major")
    parser.add_argument("--alpha-threshold", type=int, default=8)
    parser.add_argument("--safe-margin", type=int)
    parser.add_argument("--require-transparent-corners", action="store_true")
    parser.add_argument("--allow-empty-frames", action="store_true")
    parser.add_argument("--allow-nonempty-unused-cells", action="store_true")
    parser.add_argument("--max-transparent-rgb", type=int, default=0)
    parser.add_argument("--require-closed-loop", action="store_true")
    parser.add_argument(
        "--closed-loop-range",
        action="append",
        default=[],
        metavar="LABEL:START:COUNT",
        help="Require exact repeated endpoints in a 1-based frame range; repeat for multiple clips",
    )
    parser.add_argument("--max-centroid-drift", type=float)
    parser.add_argument("--min-vertical-travel", type=float)
    parser.add_argument("--max-vertical-travel", type=float)
    parser.add_argument(
        "--contact-rows",
        type=int,
        help="Bottom contact-band rows compared across frames",
    )
    parser.add_argument("--max-contact-difference", type=float)
    parser.add_argument("--min-partial-alpha-ratio", type=float)
    parser.add_argument("--max-partial-alpha-ratio", type=float)
    parser.add_argument("--min-unique-colors", type=int)
    parser.add_argument("--max-unique-colors", type=int)
    return parser.parse_args()


def cell_position(index: int, columns: int, rows: int, order: str) -> tuple[int, int]:
    if order == "row-major":
        return index % columns, index // columns
    return index // rows, index % rows


def visible_bbox(frame: np.ndarray, threshold: int) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(frame[..., 3] > threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def alpha_centroid_x(frame: np.ndarray) -> float:
    alpha = frame[..., 3].astype(np.float64)
    total = alpha.sum()
    x = np.arange(frame.shape[1], dtype=np.float64)[None, :]
    return float((alpha * x).sum() / total)


def mean_abs_difference(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())


def parse_loop_range(spec: str, frame_count: int) -> tuple[str, int, int]:
    try:
        label, raw_start, raw_count = spec.rsplit(":", 2)
        start = int(raw_start)
        count = int(raw_count)
    except ValueError as error:
        raise ValueError(f"invalid --closed-loop-range {spec!r}; expected LABEL:START:COUNT") from error
    if not label or start < 1 or count < 2 or start + count - 1 > frame_count:
        raise ValueError(f"closed loop range is outside 1..{frame_count}: {spec!r}")
    return label, start - 1, count


def validate_args(args: argparse.Namespace, frame_width: int, frame_height: int) -> tuple[int, int]:
    if args.frame_count < 1:
        raise ValueError("--frame-count must be positive")
    columns = args.columns or args.frame_count
    if columns < 1 or columns > args.frame_count:
        raise ValueError("--columns must be between 1 and --frame-count")
    if not 0 <= args.alpha_threshold <= 254:
        raise ValueError("--alpha-threshold must be between 0 and 254")
    if args.safe_margin is not None and args.safe_margin < 0:
        raise ValueError("--safe-margin must be non-negative")
    if args.contact_rows is not None and not 1 <= args.contact_rows <= frame_height:
        raise ValueError("--contact-rows must fit within the frame height")
    for value, name in (
        (args.min_partial_alpha_ratio, "--min-partial-alpha-ratio"),
        (args.max_partial_alpha_ratio, "--max-partial-alpha-ratio"),
    ):
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")
    rows = math.ceil(args.frame_count / columns)
    return columns, rows


def main() -> int:
    args = parse_args()
    frame_width, frame_height = resolve_frame_dimensions(
        args.frame_size,
        args.frame_width,
        args.frame_height,
    )
    columns, rows = validate_args(args, frame_width, frame_height)
    loop_ranges = [parse_loop_range(spec, args.frame_count) for spec in args.closed_loop_range]

    image = Image.open(args.sheet)
    checks: list[Check] = []
    expected_size = (columns * frame_width, rows * frame_height)
    checks.append(Check("sheet-size", image.size == expected_size, f"actual={image.size}, expected={expected_size}"))
    checks.append(Check("rgba", image.mode == "RGBA", f"mode={image.mode}"))
    if image.size != expected_size:
        for check in checks:
            print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
        return 1

    rgba = np.asarray(image.convert("RGBA"))
    used_cells: set[tuple[int, int]] = set()
    frames: list[np.ndarray] = []
    for index in range(args.frame_count):
        column, row = cell_position(index, columns, rows, args.order)
        used_cells.add((column, row))
        x = column * frame_width
        y = row * frame_height
        frames.append(rgba[y : y + frame_height, x : x + frame_width, :])

    unused_cells = [
        (column, row)
        for row in range(rows)
        for column in range(columns)
        if (column, row) not in used_cells
    ]
    unused_alpha = 0
    for column, row in unused_cells:
        x = column * frame_width
        y = row * frame_height
        cell = rgba[y : y + frame_height, x : x + frame_width, :]
        unused_alpha = max(unused_alpha, int(cell[..., 3].max(initial=0)))
    if unused_cells and not args.allow_nonempty_unused_cells:
        checks.append(
            Check(
                "unused-cells-transparent",
                unused_alpha == 0,
                f"cells={len(unused_cells)}, maximum alpha={unused_alpha}",
            ),
        )

    bboxes = [visible_bbox(frame, args.alpha_threshold) for frame in frames]
    empty_indices = [index + 1 for index, bbox in enumerate(bboxes) if bbox is None]
    if not args.allow_empty_frames:
        checks.append(Check("visible-content", not empty_indices, f"empty frames={empty_indices}"))
    populated = [(frame, bbox) for frame, bbox in zip(frames, bboxes, strict=True) if bbox is not None]

    transparent_rgb = int(rgba[..., :3][rgba[..., 3] == 0].max(initial=0))
    checks.append(
        Check(
            "transparent-rgb-clean",
            transparent_rgb <= args.max_transparent_rgb,
            f"maximum RGB under alpha=0 is {transparent_rgb}, maximum={args.max_transparent_rgb}",
        ),
    )

    if args.safe_margin is not None and populated:
        minimum_margin = min(
            min(left, top, frame_width - right, frame_height - bottom)
            for _, (left, top, right, bottom) in populated
        )
        checks.append(
            Check(
                "safe-margin",
                minimum_margin >= args.safe_margin,
                f"minimum={minimum_margin}px, required={args.safe_margin}px",
            ),
        )

    if args.require_transparent_corners:
        corner_alpha = max(
            int(frame[[0, 0, -1, -1], [0, -1, 0, -1], 3].max())
            for frame in frames
        )
        checks.append(Check("transparent-corners", corner_alpha <= args.alpha_threshold, f"maximum alpha={corner_alpha}"))

    if args.require_closed_loop:
        closed = np.array_equal(frames[0], frames[-1])
        checks.append(Check("closed-loop", closed, f"frame 1 equals frame {args.frame_count}: {closed}"))
    for label, start, count in loop_ranges:
        closed = np.array_equal(frames[start], frames[start + count - 1])
        checks.append(
            Check(
                f"closed-loop:{label}",
                closed,
                f"frame {start + 1} equals frame {start + count}: {closed}",
            ),
        )

    if populated and args.max_centroid_drift is not None:
        centroids = [alpha_centroid_x(frame) for frame, _ in populated]
        centroid_drift = max(centroids) - min(centroids)
        checks.append(
            Check(
                "horizontal-stability",
                centroid_drift <= args.max_centroid_drift,
                f"centroid range={centroid_drift:.3f}px, maximum={args.max_centroid_drift:.3f}px",
            ),
        )

    if populated and (args.min_vertical_travel is not None or args.max_vertical_travel is not None):
        tops = [bbox[1] for _, bbox in populated]
        vertical_travel = float(max(tops) - min(tops))
        minimum = args.min_vertical_travel if args.min_vertical_travel is not None else 0.0
        maximum = args.max_vertical_travel if args.max_vertical_travel is not None else math.inf
        checks.append(
            Check(
                "vertical-travel",
                minimum <= vertical_travel <= maximum,
                f"top travel={vertical_travel:.1f}px, expected={minimum:.1f}-{maximum:.1f}px",
            ),
        )

    if len(populated) == len(frames) and args.contact_rows is not None and args.max_contact_difference is not None:
        global_top = min(bbox[1] for _, bbox in populated)
        global_bottom = max(bbox[3] for _, bbox in populated)
        contact_start = max(global_top, global_bottom - args.contact_rows)
        contact_reference = frames[0][contact_start:global_bottom]
        contact_difference = max(
            mean_abs_difference(contact_reference, frame[contact_start:global_bottom])
            for frame in frames[1:]
        )
        checks.append(
            Check(
                "contact-lock",
                contact_difference <= args.max_contact_difference,
                f"maximum mean RGBA difference={contact_difference:.3f}, maximum={args.max_contact_difference:.3f}",
            ),
        )

    if populated and any(
        value is not None
        for value in (
            args.min_partial_alpha_ratio,
            args.max_partial_alpha_ratio,
            args.min_unique_colors,
            args.max_unique_colors,
        )
    ):
        partial_ratios = []
        unique_colors = []
        for frame, _ in populated:
            alpha = frame[..., 3]
            visible = np.count_nonzero(alpha > 0)
            partial = np.count_nonzero((alpha > 0) & (alpha < 255))
            partial_ratios.append(partial / max(1, visible))
            unique_colors.append(len(np.unique(frame.reshape(-1, 4), axis=0)))
        median_partial = float(np.median(partial_ratios))
        median_colors = int(np.median(unique_colors))
        if args.min_partial_alpha_ratio is not None:
            checks.append(
                Check(
                    "partial-alpha-minimum",
                    median_partial >= args.min_partial_alpha_ratio,
                    f"median={median_partial:.3f}, minimum={args.min_partial_alpha_ratio:.3f}",
                ),
            )
        if args.max_partial_alpha_ratio is not None:
            checks.append(
                Check(
                    "partial-alpha-maximum",
                    median_partial <= args.max_partial_alpha_ratio,
                    f"median={median_partial:.3f}, maximum={args.max_partial_alpha_ratio:.3f}",
                ),
            )
        if args.min_unique_colors is not None:
            checks.append(
                Check(
                    "unique-colors-minimum",
                    median_colors >= args.min_unique_colors,
                    f"median={median_colors}, minimum={args.min_unique_colors}",
                ),
            )
        if args.max_unique_colors is not None:
            checks.append(
                Check(
                    "unique-colors-maximum",
                    median_colors <= args.max_unique_colors,
                    f"median={median_colors}, maximum={args.max_unique_colors}",
                ),
            )

    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
    failures = [check for check in checks if not check.passed]
    print(f"summary: {len(checks) - len(failures)}/{len(checks)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
