"""Deterministic package construction from a normalized production model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from .errors import ContractError
from .package_io import atomic_directory, cell_position, image_record, sha256_file
from .production import parse_production_request
from .protocol import PACKAGE_SCHEMA
from .rendering import (
    MAX_HIGH_RESOLUTION_SIDE,
    MAX_PNG_DECODED_PIXELS,
    clear_transparent_rgb,
    render_high_resolution_source,
    rendering_frame_record,
    rendering_receipt,
)


def build_package(request_path: Path, output_dir: Path) -> None:
    parsed = parse_production_request(request_path)

    def build(destination: Path) -> None:
        artifacts_dir = destination / "artifacts"
        artifacts_dir.mkdir()
        admission_dir = destination / "admission"
        admission_dir.mkdir()
        evidence_dir = destination / "evidence"
        evidence_dir.mkdir()
        admission_records: list[dict[str, Any]] = []
        for canonical_id in parsed["canonical_ids"]:
            admission = parsed["admissions"][canonical_id]
            proof_hash = admission["proof_sha256"]
            proof_relative = f"admission/{proof_hash}.json"
            (destination / proof_relative).write_bytes(admission["proof_bytes"])
            source_hash = admission["proof"]["source"]["sha256"]
            source_relative = f"evidence/{source_hash}.png"
            source_destination = destination / source_relative
            if not source_destination.exists():
                source_destination.write_bytes(admission["source_bytes"])
            evidence_hash = admission["evidence_sha256"]
            evidence_relative = f"evidence/{evidence_hash}.json"
            (destination / evidence_relative).write_bytes(admission["evidence_bytes"])
            admission_records.append(
                {
                    "canonical_reference": canonical_id,
                    "proof_path": proof_relative,
                    "proof_sha256": proof_hash,
                    "source_path": source_relative,
                    "source_sha256": source_hash,
                    "evidence_path": evidence_relative,
                    "evidence_sha256": evidence_hash,
                },
            )
        artifact_records: list[dict[str, Any]] = []
        for artifact_id in parsed["canonical_ids"] + parsed["frame_ids"]:
            digest = parsed["hashes"][artifact_id]
            relative = f"artifacts/{digest}.png"
            destination_path = destination / relative
            if not destination_path.exists():
                destination_path.write_bytes(parsed["artifact_bytes"][artifact_id])
            image = parsed["images"][artifact_id]
            if artifact_id in parsed["canonical_ids"]:
                artifact_records.append(
                    image_record(artifact_id, "canonical-reference", relative, image, digest),
                )
            else:
                role = next(
                    frame["role"]
                    for clip in parsed["clips"]
                    for frame in clip["frames"]
                    if frame["id"] == artifact_id
                )
                bracket = next(
                    frame
                    for clip in parsed["clips"]
                    for frame in clip["frames"]
                    if frame["id"] == artifact_id
                )
                bracket_fields = {
                    key: bracket[key]
                    for key in ("previous_keyframe", "next_keyframe")
                    if key in bracket
                }
                artifact_records.append(
                    image_record(
                        artifact_id,
                        "high-resolution-frame-source",
                        relative,
                        image,
                        digest,
                        role=role,
                        canonical_reference=next(
                            clip["canonical_reference"]
                            for clip in parsed["clips"]
                            if any(frame["id"] == artifact_id for frame in clip["frames"])
                        ),
                        **bracket_fields,
                    ),
                )

        sampled: dict[str, Image.Image] = {}
        receipt_frames: list[dict[str, Any]] = []
        resolved_outline_width: int | None = None
        for frame_id in parsed["frame_ids"]:
            outlined, cell, frame_outline_width = render_high_resolution_source(
                parsed["images"][frame_id],
                parsed["contract"]["outline"],
                (parsed["frame_width"], parsed["frame_height"]),
            )
            if resolved_outline_width is None:
                resolved_outline_width = frame_outline_width
            elif resolved_outline_width != frame_outline_width:
                raise ContractError("resolved high-resolution outline width must be consistent")
            sampled[frame_id] = cell
            receipt_frames.append(
                rendering_frame_record(frame_id, parsed["hashes"][frame_id], outlined, cell),
            )
        cells: list[dict[str, Any]] = []
        for clip in parsed["clips"]:
            frames = clip.pop("frames")
            clip["frame_ids"] = [frame["id"] for frame in frames]
            for frame in frames:
                cells.append({"source": frame["id"], "repeated_opening": False})
            if clip["repeat_opening_cell"]:
                cells.append({"source": clip["frame_ids"][0], "repeated_opening": True})

        columns = parsed["columns"]
        rows = (parsed["frame_count"] + columns - 1) // columns
        sheet_width = columns * parsed["frame_width"]
        sheet_height = rows * parsed["frame_height"]
        if (
            max(sheet_width, sheet_height) > MAX_HIGH_RESOLUTION_SIDE
            or sheet_width * sheet_height > MAX_PNG_DECODED_PIXELS
        ):
            raise ContractError("sheet dimensions exceed bounded deterministic rendering limits")
        sheet = Image.new(
            "RGBA",
            (sheet_width, sheet_height),
            (0, 0, 0, 0),
        )
        for index, cell in enumerate(cells):
            column, row = cell_position(index, columns, rows, parsed["order"])
            x = column * parsed["frame_width"]
            y = row * parsed["frame_height"]
            sheet.alpha_composite(sampled[cell["source"]], (x, y))
            cell.update({"index": index, "column": column, "row": row})
        sheet_path = destination / "spritesheet.png"
        sheet = clear_transparent_rgb(sheet)
        sheet.save(sheet_path)
        artifact_records.append(
            image_record(
                "spritesheet",
                "spritesheet",
                sheet_path.name,
                sheet,
                sha256_file(sheet_path),
            ),
        )
        manifest = {
            "schema_version": PACKAGE_SCHEMA,
            "contract": parsed["contract"],
            "artifacts": artifact_records,
            "canonical_admissions": admission_records,
            "clips": parsed["clips"],
            "reviews": parsed["reviews"],
            "rendering": rendering_receipt(
                parsed["contract"]["outline"],
                resolved_outline_width or 0,
                receipt_frames,
                hashlib.sha256(sheet.tobytes()).hexdigest(),
            ),
            "assembly": {
                "sheet": "spritesheet",
                "columns": columns,
                "rows": rows,
                "order": parsed["order"],
                "cells": cells,
            },
        }
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        from .verification import verify_package

        if not verify_package(manifest_path, emit=False):
            raise ContractError("generated package did not pass verification")

    atomic_directory(output_dir, build)
