"""Deterministic measurement and review renderings for verified v4 packages."""

from __future__ import annotations

import subprocess
import sys
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .errors import EvidenceError
from .io import (
    MAX_FILE_BYTES,
    atomic_directory,
    copy_bound_file,
    read_json,
    reject_path_overlap,
    require_regular_file,
    reserve_build_budget,
    sha256_file,
    write_canonical_json,
)
from .schemas import DIAGNOSTICS_SCHEMA, validate_document

MAX_IMAGE_PIXELS = 64 * 1024 * 1024
MAX_CELLS = 4096
VERIFY_TIMEOUT_SECONDS = 180


def _verify_package(manifest_path: Path, pipeline_path: Path) -> None:
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(pipeline_path),
                "verify-package",
                "--manifest",
                str(manifest_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT_SECONDS,
            env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as error:
        raise EvidenceError(
            "PACKAGE_VERIFY_TIMEOUT", "verify-package exceeded its bounded runtime"
        ) from error
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise EvidenceError(
            "PACKAGE_VERIFY_FAILED", detail[-4000:] or "verify-package failed"
        )


def _open_rgba(path: Path, location: str) -> Image.Image:
    require_regular_file(path, location, max_bytes=MAX_FILE_BYTES)
    try:
        with Image.open(path) as opened:
            if opened.width * opened.height > MAX_IMAGE_PIXELS:
                raise EvidenceError(
                    "RESOURCE_LIMIT", f"{location} exceeds decoded pixel limit"
                )
            if opened.mode != "RGBA":
                raise EvidenceError("IMAGE_INVALID", f"{location} must decode as RGBA")
            return opened.copy()
    except EvidenceError:
        raise
    except (OSError, ValueError) as error:
        raise EvidenceError(
            "IMAGE_INVALID", f"cannot decode {location}: {error}"
        ) from error


def _crop_cells(manifest: dict[str, Any], sheet: Image.Image) -> list[Image.Image]:
    contract = manifest["contract"]
    width = contract["frame_width"]
    height = contract["frame_height"]
    cells = manifest["assembly"]["cells"]
    if len(cells) > MAX_CELLS:
        raise EvidenceError("RESOURCE_LIMIT", f"package exceeds {MAX_CELLS} cells")
    return [
        sheet.crop(
            (
                cell["column"] * width,
                cell["row"] * height,
                (cell["column"] + 1) * width,
                (cell["row"] + 1) * height,
            ),
        )
        for cell in cells
    ]


def _rounded_point(x: float, y: float) -> list[float]:
    return [round(x, 6), round(y, 6)]


def _cell_metrics(
    image: Image.Image,
    previous: Image.Image | None,
    index: int,
    source: str,
    anchor: list[int],
    safe_bounds: list[int],
) -> dict[str, Any]:
    pixels = np.asarray(image, dtype=np.uint8)
    alpha = pixels[..., 3]
    active_y, active_x = np.nonzero(alpha)
    bbox_raw = image.getchannel("A").getbbox()
    bbox = list(bbox_raw) if bbox_raw is not None else None
    area = int(active_x.size)
    centroid = (
        None
        if area == 0
        else _rounded_point(float(active_x.mean()), float(active_y.mean()))
    )
    anchor_offset = (
        None
        if centroid is None
        else _rounded_point(centroid[0] - anchor[0], centroid[1] - anchor[1])
    )
    left, top, right, bottom = safe_bounds
    overflow = {
        "left_pixels": int(np.count_nonzero(alpha[:, :left])),
        "top_pixels": int(np.count_nonzero(alpha[:top, :])),
        "right_pixels": int(np.count_nonzero(alpha[:, right:])),
        "bottom_pixels": int(np.count_nonzero(alpha[bottom:, :])),
    }
    clipped: list[str] = []
    if np.any(alpha[:, 0]):
        clipped.append("left")
    if np.any(alpha[0, :]):
        clipped.append("top")
    if np.any(alpha[:, -1]):
        clipped.append("right")
    if np.any(alpha[-1, :]):
        clipped.append("bottom")
    difference = None
    if previous is not None:
        prior = np.asarray(previous, dtype=np.uint8)
        absolute = np.abs(pixels.astype(np.int16) - prior.astype(np.int16))
        difference = {
            "changed_pixels": int(np.count_nonzero(np.any(pixels != prior, axis=2))),
            "rgba_absolute_difference": int(absolute.sum(dtype=np.int64)),
        }
    return {
        "index": index,
        "source": source,
        "alpha_bbox": bbox,
        "alpha_area": area,
        "alpha_centroid": centroid,
        "anchor_offset": anchor_offset,
        "safe_bounds_overflow": overflow,
        "clipped_edges": clipped,
        "pixel_diff_from_previous": difference,
    }


def _checkerboard(size: tuple[int, int]) -> Image.Image:
    width, height = size
    board = Image.new("RGBA", size, (40, 40, 40, 255))
    block = 8
    for y in range(0, height, block):
        for x in range(0, width, block):
            if (x // block + y // block) % 2:
                board.paste(
                    (64, 64, 64, 255),
                    (x, y, min(x + block, width), min(y + block, height)),
                )
    return board


def _contact_sheet(sheet: Image.Image) -> Image.Image:
    if sheet.width * sheet.height * 16 > MAX_IMAGE_PIXELS:
        raise EvidenceError(
            "RESOURCE_LIMIT", "contact sheet exceeds derived pixel limit"
        )
    return sheet.resize((sheet.width * 4, sheet.height * 4), Image.Resampling.NEAREST)


def _native_board(cells: list[Image.Image]) -> Image.Image:
    width = sum(cell.width for cell in cells)
    height = cells[0].height
    if width * height > MAX_IMAGE_PIXELS:
        raise EvidenceError(
            "RESOURCE_LIMIT", "native-size board exceeds derived pixel limit"
        )
    board = _checkerboard((width, height))
    x = 0
    for cell in cells:
        board.alpha_composite(cell, (x, 0))
        x += cell.width
    return board


def _tint_alpha(image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    tinted = Image.new("RGBA", image.size, (*color, 0))
    tinted.putalpha(image.getchannel("A").point(lambda value: value // 2))
    return tinted


def _onion_board(clip_cells: list[list[Image.Image]]) -> Image.Image:
    pairs: list[tuple[Image.Image, Image.Image]] = []
    for cells in clip_cells:
        pairs.extend(
            list(pairwise(cells)) if len(cells) > 1 else [(cells[0], cells[0])]
        )
    cells = clip_cells[0]
    if cells[0].width * len(pairs) * cells[0].height > MAX_IMAGE_PIXELS:
        raise EvidenceError(
            "RESOURCE_LIMIT", "onion-skin board exceeds derived pixel limit"
        )
    board = _checkerboard((cells[0].width * len(pairs), cells[0].height))
    for index, (previous, current) in enumerate(pairs):
        overlay = Image.new("RGBA", previous.size, (0, 0, 0, 0))
        overlay.alpha_composite(_tint_alpha(previous, (255, 64, 64)))
        overlay.alpha_composite(_tint_alpha(current, (64, 255, 255)))
        board.alpha_composite(overlay, (index * previous.width, 0))
    return board


def _asset_ref(path: Path, root: Path) -> dict[str, str]:
    return {"ref": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def diagnose(manifest_path: Path, output_dir: Path, pipeline_path: Path) -> None:
    manifest_path = require_regular_file(manifest_path, "manifest")
    reject_path_overlap(output_dir, [manifest_path.parent, manifest_path])
    reserve_build_budget([manifest_path.parent], derived_bytes=64 * 1024 * 1024)
    if manifest_path.name != "manifest.json":
        raise EvidenceError("PACKAGE_INVALID", "manifest must be named manifest.json")
    _verify_package(manifest_path, pipeline_path)
    manifest = read_json(manifest_path, "manifest")
    sheet_record = next(
        (
            artifact
            for artifact in manifest["artifacts"]
            if artifact.get("id") == manifest["assembly"]["sheet"]
        ),
        None,
    )
    if not isinstance(sheet_record, dict):
        raise EvidenceError(
            "PACKAGE_INVALID", "manifest does not reference a spritesheet artifact"
        )
    sheet_path = manifest_path.parent / sheet_record["path"]
    if sheet_path.is_symlink():
        raise EvidenceError("SYMLINK_FORBIDDEN", "spritesheet must not be a symlink")
    sheet = _open_rgba(sheet_path.resolve(), "spritesheet")
    cells = _crop_cells(manifest, sheet)
    contract = manifest["contract"]
    assembly_cells = manifest["assembly"]["cells"]

    def build(destination: Path) -> None:
        source_dir = destination / "source"
        source_dir.mkdir()
        manifest_copy = source_dir / "manifest.json"
        copy_bound_file(manifest_path, manifest_copy, sha256_file(manifest_path))
        contact_path = destination / "contact-sheet.png"
        native_path = destination / "native-size-board.png"
        onion_path = destination / "onion-skin.png"
        _contact_sheet(sheet).save(contact_path, optimize=False, compress_level=9)
        _native_board(cells).save(native_path, optimize=False, compress_level=9)
        clip_cells: list[list[Image.Image]] = []
        clip_cursor = 0
        for clip in manifest["clips"]:
            clip_count = len(clip["durations_ms"])
            clip_cells.append(cells[clip_cursor : clip_cursor + clip_count])
            clip_cursor += clip_count
        _onion_board(clip_cells).save(onion_path, optimize=False, compress_level=9)
        preview_records: list[dict[str, Any]] = []
        preview_cursor = 0
        previews_dir = destination / "previews"
        previews_dir.mkdir()
        for clip_index, clip in enumerate(manifest["clips"]):
            count = len(clip["durations_ms"])
            frames = [
                cell.convert("RGBA")
                for cell in cells[preview_cursor : preview_cursor + count]
            ]
            preview_path = previews_dir / f"{clip_index:04d}.gif"
            gif_options: dict[str, Any] = {"loop": 0} if clip["loop"] else {}
            frames[0].save(
                preview_path,
                save_all=True,
                append_images=frames[1:],
                duration=clip["durations_ms"],
                disposal=2,
                optimize=False,
                **gif_options,
            )
            preview_records.append(
                {"clip_id": clip["id"], "asset": _asset_ref(preview_path, destination)}
            )
            preview_cursor += count
        clip_records: list[dict[str, Any]] = []
        cursor = 0
        for clip in manifest["clips"]:
            count = len(clip["durations_ms"])
            metrics = []
            for offset in range(count):
                global_index = cursor + offset
                metrics.append(
                    _cell_metrics(
                        cells[global_index],
                        cells[global_index - 1] if offset > 0 else None,
                        global_index,
                        assembly_cells[global_index]["source"],
                        contract["anchor"],
                        contract["safe_bounds"],
                    ),
                )
            clip_records.append({"clip_id": clip["id"], "cells": metrics})
            cursor += count
        diagnostics = {
            "schema_version": DIAGNOSTICS_SCHEMA,
            "package_manifest": _asset_ref(manifest_copy, destination),
            "assets": {
                "contact_sheet": _asset_ref(contact_path, destination),
                "native_size_board": _asset_ref(native_path, destination),
                "onion_skin": _asset_ref(onion_path, destination),
            },
            "previews": preview_records,
            "clips": clip_records,
            "observations": [],
        }
        validate_document(diagnostics, DIAGNOSTICS_SCHEMA)
        write_canonical_json(destination / "motion-diagnostics.json", diagnostics)

    atomic_directory(output_dir, build)
