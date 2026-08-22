"""Admit final raw high-resolution frame sources before visual review."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from spritesheet_core.errors import ContractError
from spritesheet_core.rendering import open_rgba_snapshot, resolve_high_resolution_dimensions

from .contracts import ProductionError
from .io import atomic_canonical_json, digest_value, sha256_file

RAW_FRAME_ADMISSION_SCHEMA = "raw-frame-admission/v1"


def _position(state: dict[str, Any], frame_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for clip in state["intent"]["clips"]:
        for position in clip["positions"]:
            if position["id"] == frame_id:
                return clip, position
    raise ProductionError("RAW_FRAME_ADMISSION_FAILED", "frame is not bound to the approved motion plan")


def admit_raw_frame(
    job: Path,
    state: dict[str, Any],
    frame_id: str,
    frozen_source: Path,
) -> tuple[str, str]:
    """Return the admitted source path and its atomic evidence path."""
    clip, position = _position(state, frame_id)
    if position["role"] == "alias":
        raise ProductionError("RAW_FRAME_ADMISSION_FAILED", "an alias cannot provide a raw source")
    target = state["intent"]["target"]
    expected_size, _ = resolve_high_resolution_dimensions(target["frame_width"], target["frame_height"])
    try:
        image, snapshot = open_rgba_snapshot(
            frozen_source,
            f"raw frame {frame_id!r}",
        )
        if image.size != expected_size:
            raise ContractError(
                f"raw frame {frame_id!r} dimensions must equal {expected_size[0]}x{expected_size[1]}"
            )
    except (ContractError, OSError, ValueError, TypeError) as error:
        raise ProductionError(
            "RAW_FRAME_ADMISSION_FAILED",
            "raw frame must be a bounded RGBA PNG on the required high-resolution canvas",
            {"frame_id": frame_id},
        ) from error
    rgba = np.asarray(image, dtype=np.uint8)
    alpha = rgba[..., 3]
    nonzero = alpha > 0
    if not np.any(nonzero):
        raise ProductionError("RAW_FRAME_ADMISSION_FAILED", "raw frame must contain visible Alpha", {"frame_id": frame_id})
    hidden_rgb = (alpha == 0) & np.any(rgba[..., :3] != 0, axis=2)
    hidden_rgb_pixels = int(np.count_nonzero(hidden_rgb))
    thresholds = state["intent"]["rendering_profile"]["quality_thresholds"]
    policy = thresholds["transparent_rgb"]
    if hidden_rgb_pixels:
        raise ProductionError(
            "RAW_FRAME_ADMISSION_FAILED",
            "raw frame contains RGB beneath zero Alpha",
            {"frame_id": frame_id, "transparent_rgb_pixels": hidden_rgb_pixels},
        )
    ys, xs = np.nonzero(nonzero)
    left = int(xs.min())
    top = int(ys.min())
    right = int(xs.max()) + 1
    bottom = int(ys.max()) + 1
    margins = [left, top, image.width - right, image.height - bottom]
    minimum_margin = thresholds["minimum_margin"]
    if min(margins) < minimum_margin:
        raise ProductionError(
            "RAW_FRAME_ADMISSION_FAILED",
            "raw frame does not satisfy the configured high-resolution margin",
            {"frame_id": frame_id, "margins": margins, "minimum_margin": minimum_margin},
        )
    opaque_pixels = int(np.count_nonzero(alpha == 255))
    partial_alpha_pixels = int(np.count_nonzero((alpha > 0) & (alpha < 255)))
    alpha_total = float(alpha.sum())
    centroid = [
        round(float((xs * alpha[ys, xs]).sum()) / alpha_total, 6),
        round(float((ys * alpha[ys, xs]).sum()) / alpha_total, 6),
    ]
    motion_plan_path = Path(state["outputs"]["motion_plan"])
    document = {
        "schema_version": RAW_FRAME_ADMISSION_SCHEMA,
        "frame_id": frame_id,
        "canonical_view": clip["canonical_view"],
        "plan_binding": {
            "motion_plan_sha256": sha256_file(motion_plan_path),
            "position_sha256": digest_value(position),
        },
        "source": {
            "sha256": snapshot.sha256,
            "rgba_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        },
        "alpha": {
            "nonzero_bounds": [left, top, right, bottom],
            "margins": margins,
            "opaque_pixels": opaque_pixels,
            "partial_alpha_pixels": partial_alpha_pixels,
            "transparent_rgb_pixels_observed": hidden_rgb_pixels,
            "centroid": centroid,
        },
        "policy": {
            "transparent_rgb": policy,
            "minimum_margin": minimum_margin,
            "normalized": False,
            "status": "passed",
        },
    }
    admission_path = job / f"artifacts-r{state['material_revision']}" / f"raw-frame-admission-{frame_id}.json"
    atomic_canonical_json(admission_path, document)
    return str(frozen_source), str(admission_path)
