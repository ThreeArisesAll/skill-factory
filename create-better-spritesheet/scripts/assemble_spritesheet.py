#!/usr/bin/env python3
"""Assemble contract-ordered RGBA frames into a rectangular spritesheet grid."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble exact-size RGBA frames into a row-major or column-major grid.",
    )
    parser.add_argument("--frames-dir", required=True, type=Path)
    parser.add_argument("--pattern", default="*.png", help="Frame filename glob")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", type=Path, help="Defaults to the output path with .json suffix")
    parser.add_argument("--frame-width", required=True, type=int)
    parser.add_argument("--frame-height", required=True, type=int)
    parser.add_argument("--frame-count", required=True, type=int)
    parser.add_argument("--columns", required=True, type=int)
    parser.add_argument("--order", choices=("row-major", "column-major"), default="row-major")
    parser.add_argument(
        "--clip",
        action="append",
        default=[],
        metavar="LABEL:START:COUNT",
        help="Record a 1-based clip range in metadata; repeat for multiple clips",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def natural_key(path: Path) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def cell_position(index: int, columns: int, rows: int, order: str) -> tuple[int, int]:
    if order == "row-major":
        return index % columns, index // columns
    return index // rows, index % rows


def parse_clip_range(spec: str, frame_count: int) -> dict[str, int | str]:
    try:
        label, raw_start, raw_count = spec.rsplit(":", 2)
        start = int(raw_start)
        count = int(raw_count)
    except ValueError as error:
        raise ValueError(f"invalid --clip {spec!r}; expected LABEL:START:COUNT") from error
    if not label or start < 1 or count < 1 or start + count - 1 > frame_count:
        raise ValueError(f"clip range is outside 1..{frame_count}: {spec!r}")
    return {
        "label": label,
        "start_index": start - 1,
        "start_frame": start,
        "count": count,
    }


def validate_args(args: argparse.Namespace) -> None:
    if args.frame_width < 1 or args.frame_height < 1:
        raise ValueError("frame dimensions must be positive")
    if args.frame_count < 1:
        raise ValueError("--frame-count must be positive")
    if args.columns < 1 or args.columns > args.frame_count:
        raise ValueError("--columns must be between 1 and --frame-count")
    if not args.frames_dir.is_dir():
        raise ValueError(f"frames directory does not exist: {args.frames_dir}")


def prepare_output(output: Path, metadata: Path, overwrite: bool) -> None:
    for path in (output, metadata):
        if path.exists() and not overwrite:
            raise FileExistsError(f"output already exists: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    validate_args(args)
    clips = [parse_clip_range(spec, args.frame_count) for spec in args.clip]
    metadata_path = args.metadata or args.output.with_suffix(".json")
    prepare_output(args.output, metadata_path, args.overwrite)

    frame_paths = sorted(args.frames_dir.glob(args.pattern), key=natural_key)
    if len(frame_paths) != args.frame_count:
        raise ValueError(
            f"matched {len(frame_paths)} frames with pattern {args.pattern!r}; "
            f"expected {args.frame_count}",
        )

    rows = math.ceil(args.frame_count / args.columns)
    sheet = Image.new(
        "RGBA",
        (args.columns * args.frame_width, rows * args.frame_height),
        (0, 0, 0, 0),
    )
    entries: list[dict[str, object]] = []
    for index, path in enumerate(frame_paths):
        image = Image.open(path)
        if image.mode != "RGBA":
            raise ValueError(f"frame must be RGBA: {path} has mode {image.mode}")
        expected = (args.frame_width, args.frame_height)
        if image.size != expected:
            raise ValueError(f"frame has wrong size: {path} is {image.size}, expected {expected}")
        column, row = cell_position(index, args.columns, rows, args.order)
        x = column * args.frame_width
        y = row * args.frame_height
        sheet.alpha_composite(image, (x, y))
        entries.append(
            {
                "index": index,
                "source": path.name,
                "column": column,
                "row": row,
                "x": x,
                "y": y,
            },
        )

    sheet.save(args.output)
    metadata = {
        "sheet": args.output.name,
        "sheet_size": [sheet.width, sheet.height],
        "frame_size": [args.frame_width, args.frame_height],
        "frame_count": args.frame_count,
        "columns": args.columns,
        "rows": rows,
        "order": args.order,
        "pattern": args.pattern,
        "clips": clips,
        "frames": entries,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"sheet: {args.output} ({sheet.width}x{sheet.height}, RGBA)")
    print(
        f"frames: {args.frame_count} at {args.frame_width}x{args.frame_height}; "
        f"grid={args.columns}x{rows}; order={args.order}",
    )
    print(f"metadata: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
