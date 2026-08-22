"""Typed normalized production request model and parser."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .admission import canonical_admission_proof
from .errors import ContractError
from .package_io import ResourceBudget, read_regular_file_snapshot
from .protocol import (
    CONTRACT_KEYS,
    HIGH_RESOLUTION_SHORT_SIDE,
    MAX_CANONICAL_REFERENCES,
    MAX_CLIPS,
    MAX_FRAME_COUNT,
    MAX_JSON_FILE_BYTES,
    PRODUCTION_REQUEST_SCHEMA,
    PRODUCTION_REQUEST_SCHEMA_V5,
    SAMPLER,
    normalize_clip_metadata,
    read_request,
    require_absolute_path,
    require_exact_keys,
    require_object,
    require_positive_int,
    require_string,
    validate_bounds,
    validate_outline_contract,
    validate_point,
    validate_review_requests,
)
from .rendering import open_rgba_snapshot, resolve_high_resolution_dimensions


@dataclass(frozen=True)
class ProductionModel(Mapping[str, Any]):
    """Validated production state with mapping compatibility for stable internals."""

    schema_version: str
    contract: dict[str, Any]
    frame_width: int
    frame_height: int
    frame_count: int
    high_resolution_size: tuple[int, int]
    animation_origin: list[int]
    anchor: list[int]
    safe_bounds: list[int]
    canonical_ids: list[str]
    images: dict[str, Image.Image]
    paths: dict[str, Path]
    hashes: dict[str, str]
    artifact_bytes: dict[str, bytes]
    admissions: dict[str, dict[str, Any]]
    clips: list[dict[str, Any]]
    frame_ids: list[str]
    reviews: list[dict[str, Any]]
    columns: int
    order: str

    _FIELDS = (
        "schema_version",
        "contract",
        "frame_width",
        "frame_height",
        "frame_count",
        "high_resolution_size",
        "animation_origin",
        "anchor",
        "safe_bounds",
        "canonical_ids",
        "images",
        "paths",
        "hashes",
        "artifact_bytes",
        "admissions",
        "clips",
        "frame_ids",
        "reviews",
        "columns",
        "order",
    )

    def __getitem__(self, key: str) -> Any:
        if key not in self._FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._FIELDS)

    def __len__(self) -> int:
        return len(self._FIELDS)
def parse_production_request(request_path: Path) -> ProductionModel:
    budget = ResourceBudget()
    request = read_request(
        request_path,
        {PRODUCTION_REQUEST_SCHEMA, PRODUCTION_REQUEST_SCHEMA_V5},
        budget=budget,
    )
    is_v5 = request["schema_version"] == PRODUCTION_REQUEST_SCHEMA_V5
    require_exact_keys(
        request,
        {"schema_version", "contract", "canonical_references", "clips", "reviews", "grid"},
        "request",
    )
    contract = require_object(request.get("contract"), "contract")
    require_exact_keys(contract, CONTRACT_KEYS, "contract")
    frame_width = require_positive_int(contract.get("frame_width"), "contract.frame_width")
    frame_height = require_positive_int(contract.get("frame_height"), "contract.frame_height")
    frame_count = require_positive_int(contract.get("frame_count"), "contract.frame_count")
    if frame_count > MAX_FRAME_COUNT:
        raise ContractError(f"contract.frame_count must not exceed {MAX_FRAME_COUNT}")
    expected_high_resolution_size, _ = resolve_high_resolution_dimensions(frame_width, frame_height)
    if contract.get("high_resolution_short_side") != HIGH_RESOLUTION_SHORT_SIDE:
        raise ContractError("contract.high_resolution_short_side must be 512")
    if contract.get("sampler") != SAMPLER:
        raise ContractError(f"contract.sampler must be {SAMPLER!r}")
    normalized_outline = validate_outline_contract(contract.get("outline"), "contract.outline")
    if normalized_outline["enabled"] and normalized_outline["target_width"] >= min(frame_width, frame_height):
        raise ContractError("contract.outline.target_width must be smaller than the target shortest side")
    animation_origin = validate_point(contract.get("animation_origin"), "contract.animation_origin")
    anchor = validate_point(contract.get("anchor"), "contract.anchor")
    if not (0 <= anchor[0] < frame_width and 0 <= anchor[1] < frame_height):
        raise ContractError("contract.anchor must be inside the target cell")
    safe_bounds = validate_bounds(
        contract.get("safe_bounds"),
        "contract.safe_bounds",
        frame_width,
        frame_height,
    )

    canonical_values = request.get("canonical_references")
    if not isinstance(canonical_values, list) or not canonical_values:
        raise ContractError("canonical_references must be a non-empty array")
    if len(canonical_values) > MAX_CANONICAL_REFERENCES:
        raise ContractError(
            f"canonical_references must not exceed {MAX_CANONICAL_REFERENCES} entries",
        )
    canonical: dict[str, dict[str, Any]] = {}
    admissions: dict[str, dict[str, Any]] = {}
    images: dict[str, Image.Image] = {}
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    artifact_bytes: dict[str, bytes] = {}
    for index, raw in enumerate(canonical_values):
        entry = require_object(raw, f"canonical_references[{index}]")
        require_exact_keys(
            entry,
            {"id", "path", "evidence_path", "proof_path"},
            f"canonical_references[{index}]",
        )
        artifact_id = require_string(entry.get("id"), f"canonical_references[{index}].id")
        if artifact_id == "spritesheet":
            raise ContractError("'spritesheet' is a reserved artifact id")
        if artifact_id in canonical:
            raise ContractError(f"duplicate artifact id: {artifact_id}")
        path = require_absolute_path(entry.get("path"), f"canonical_references[{index}].path")
        evidence_path = require_absolute_path(
            entry.get("evidence_path"),
            f"canonical_references[{index}].evidence_path",
        )
        proof_path = require_absolute_path(entry.get("proof_path"), f"canonical_references[{index}].proof_path")
        if path.is_symlink() or evidence_path.is_symlink() or proof_path.is_symlink():
            raise ContractError("canonical, evidence, and proof inputs must be regular non-symlink files")
        image, image_snapshot = open_rgba_snapshot(
            path,
            f"canonical_references[{index}].path",
            budget=budget,
        )
        if image.size != expected_high_resolution_size:
            raise ContractError("canonical reference has wrong high-resolution canvas")
        canonical[artifact_id] = dict(entry)
        images[artifact_id] = image
        paths[artifact_id] = path
        hashes[artifact_id] = image_snapshot.sha256
        artifact_bytes[artifact_id] = image_snapshot.data
        proof = canonical_admission_proof(
            artifact_id,
            path,
            evidence_path,
            evidence_path.parent,
            normalized_outline,
            frame_width,
            frame_height,
            budget=budget,
        )
        proof_payload = {key: value for key, value in proof.items() if not key.startswith("_")}
        expected_proof_bytes = (json.dumps(proof_payload, indent=2) + "\n").encode("utf-8")
        try:
            proof_snapshot = read_regular_file_snapshot(
                proof_path,
                "canonical admission proof",
                MAX_JSON_FILE_BYTES,
                budget=budget,
            )
            proof_bytes = proof_snapshot.data
            supplied_proof = require_object(json.loads(proof_bytes), "canonical admission proof")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ContractError(f"cannot read canonical admission proof: {error}") from error
        if supplied_proof != proof_payload or proof_bytes != expected_proof_bytes:
            raise ContractError("canonical admission proof must exactly match prepare-canonical replay output")
        admissions[artifact_id] = {
            "proof": proof_payload,
            "proof_bytes": proof_bytes,
            "proof_sha256": proof_snapshot.sha256,
            "source_path": proof["_source_path"],
            "evidence_path": proof["_evidence_path"],
            "evidence_sha256": proof_payload["authoring_evidence_sha256"],
            "source_bytes": proof["_source_bytes"],
            "evidence_bytes": proof["_evidence_bytes"],
        }

    clips_value = request.get("clips")
    if not isinstance(clips_value, list) or not clips_value:
        raise ContractError("clips must be a non-empty array")
    if len(clips_value) > MAX_CLIPS:
        raise ContractError(f"clips must not exceed {MAX_CLIPS} entries")
    clips: list[dict[str, Any]] = []
    frame_ids: list[str] = []
    clip_canonical_ids: list[str] = []
    total_cells = 0
    scoped_reviews: list[tuple[str, list[str]]] = [
        ("canonical-approval", [canonical_id])
        for canonical_id in canonical
    ]
    clip_review_scopes: list[tuple[str, list[str]]] = []
    clip_ids_seen: set[str] = set()
    logical_ids_seen: set[str] = set()
    for clip_index, raw_clip in enumerate(clips_value):
        clip = require_object(raw_clip, f"clips[{clip_index}]")
        clip_id = require_string(clip.get("id"), f"clips[{clip_index}].id")
        if clip_id in clip_ids_seen:
            raise ContractError(f"duplicate clip id: {clip_id}")
        clip_ids_seen.add(clip_id)
        canonical_id = require_string(
            clip.get("canonical_reference"),
            f"clips[{clip_index}].canonical_reference",
        )
        if canonical_id not in canonical:
            raise ContractError(f"clip {clip_id!r} references unknown canonical reference")
        clip_canonical_ids.append(canonical_id)
        loop = clip.get("loop")
        repeat = clip.get("repeat_opening_cell")
        if not isinstance(loop, bool) or not isinstance(repeat, bool):
            raise ContractError(f"clip {clip_id!r} loop and repeat_opening_cell must be boolean")
        if repeat and not loop:
            raise ContractError("repeat_opening_cell is allowed only for a loop")
        if is_v5 and repeat:
            raise ContractError("v5 requires an explicit closing alias instead of repeat_opening_cell")
        raw_frames = clip.get("frames")
        if not isinstance(raw_frames, list) or not raw_frames:
            raise ContractError(f"clip {clip_id!r} frames must be a non-empty array")
        if len(raw_frames) + total_cells > MAX_FRAME_COUNT:
            raise ContractError(f"clip cells must not exceed {MAX_FRAME_COUNT} total entries")
        clip_metadata = normalize_clip_metadata(
            clip,
            clip_id,
            len(raw_frames) + int(repeat),
            frame_width,
            frame_height,
        )
        normalized_frames: list[dict[str, Any]] = []
        local_keyframe_indices: list[int] = []
        local_concrete_ids: set[str] = set()
        for frame_index, raw_frame in enumerate(raw_frames):
            frame = require_object(raw_frame, f"clips[{clip_index}].frames[{frame_index}]")
            frame_id = require_string(frame.get("id"), f"clips[{clip_index}].frames[{frame_index}].id")
            if frame_id == "spritesheet":
                raise ContractError("'spritesheet' is a reserved artifact id")
            if frame_id in logical_ids_seen or frame_id in images:
                raise ContractError(f"duplicate artifact id: {frame_id}")
            logical_ids_seen.add(frame_id)
            role = frame.get("role")
            if is_v5 and role == "alias":
                require_exact_keys(frame, {"id", "role", "source_id", "alias_kind"}, f"frame {frame_id!r}")
                source_id = require_string(frame.get("source_id"), f"frame {frame_id!r}.source_id")
                if source_id not in local_concrete_ids:
                    raise ContractError(f"alias {frame_id!r} must reference an earlier concrete source in its clip")
                if frame.get("alias_kind") not in {"hold", "closing"}:
                    raise ContractError(f"alias {frame_id!r}.alias_kind is invalid")
                if frame.get("alias_kind") == "closing" and (not loop or frame_index != len(raw_frames) - 1):
                    raise ContractError("a closing alias must be the final position of a loop")
                normalized_frames.append(dict(frame))
                continue
            if role not in ("keyframe", "in-between"):
                raise ContractError(f"frame {frame_id!r} role must be keyframe, in-between, or a v5 alias")
            expected_frame_keys = {"id", "role", "source_path"}
            if role == "in-between":
                expected_frame_keys |= {"previous_keyframe", "next_keyframe"}
            require_exact_keys(frame, expected_frame_keys, f"frame {frame_id!r}")
            path = require_absolute_path(frame.get("source_path"), f"frame {frame_id!r}.source_path")
            image, image_snapshot = open_rgba_snapshot(
                path,
                f"frame {frame_id!r}.source_path",
                budget=budget,
            )
            if image.size != expected_high_resolution_size:
                raise ContractError(f"frame {frame_id!r} has wrong high-resolution canvas")
            images[frame_id] = image
            paths[frame_id] = path
            hashes[frame_id] = image_snapshot.sha256
            artifact_bytes[frame_id] = image_snapshot.data
            frame_ids.append(frame_id)
            local_concrete_ids.add(frame_id)
            if role == "keyframe":
                local_keyframe_indices.append(frame_index)
                if "previous_keyframe" in frame or "next_keyframe" in frame:
                    raise ContractError(f"keyframe {frame_id!r} cannot declare brackets")
            normalized_frames.append(dict(frame))
        if not is_v5 and len(local_keyframe_indices) < 2:
            raise ContractError(f"clip {clip_id!r} requires at least two distinct keyframes")
        for frame_index, frame in enumerate(normalized_frames):
            if frame["role"] != "in-between":
                continue
            previous = [index for index in local_keyframe_indices if index < frame_index]
            following = [index for index in local_keyframe_indices if index > frame_index]
            previous_index = previous[-1] if previous else (local_keyframe_indices[-1] if loop else None)
            following_index = following[0] if following else (local_keyframe_indices[0] if loop else None)
            valid = (
                previous_index is not None
                and following_index is not None
                and frame.get("previous_keyframe") == normalized_frames[previous_index]["id"]
                and frame.get("next_keyframe") == normalized_frames[following_index]["id"]
            )
            if not valid:
                raise ContractError(f"in-between {frame['id']!r} has incorrect adjacent keyframe brackets")
        if not is_v5 and sum(frame["role"] == "in-between" for frame in normalized_frames) < 2:
            raise ContractError(f"clip {clip_id!r} requires at least two distinct in-betweens")
        total_cells += len(normalized_frames) + int(repeat)
        clip_review_scopes.extend(
            (
                (
                    "keyframe-set-approval",
                    [canonical_id, *[frame["id"] for frame in normalized_frames if frame["role"] == "keyframe"]],
                ),
                (
                    "sequence-approval",
                    [
                        canonical_id,
                        *dict.fromkeys(
                            frame["source_id"] if frame["role"] == "alias" else frame["id"]
                            for frame in normalized_frames
                        ),
                    ],
                ),
            ),
        )
        clips.append(
            {
                "id": clip_id,
                "canonical_reference": canonical_id,
                "loop": loop,
                "repeat_opening_cell": repeat,
                **clip_metadata,
                "frames": normalized_frames,
            },
        )
    if set(clip_canonical_ids) != set(canonical):
        raise ContractError("every canonical reference must be consumed by at least one clip")
    if total_cells != frame_count:
        raise ContractError(f"contract.frame_count is {frame_count}, but clips declare {total_cells} cells")

    pixel_hashes = {
        artifact_id: hashlib.sha256(image.tobytes()).hexdigest()
        for artifact_id, image in images.items()
    }
    high_resolution_pixel_hashes = [pixel_hashes[frame_id] for frame_id in frame_ids]
    if not is_v5 and len(set(high_resolution_pixel_hashes)) != len(high_resolution_pixel_hashes):
        raise ContractError("all high-resolution frame images must have distinct pixels")
    canonical_pixel_hashes = [pixel_hashes[canonical_id] for canonical_id in canonical]
    if len(set(canonical_pixel_hashes)) != len(canonical_pixel_hashes):
        raise ContractError("canonical references must have distinct pixels; share one ID when content is shared")
    if not is_v5 and set(canonical_pixel_hashes) & set(high_resolution_pixel_hashes):
        raise ContractError("canonical reference must not be pixel-identical to a high-resolution frame")

    reviews = validate_review_requests(
        request.get("reviews"),
        scoped_reviews + clip_review_scopes,
        hashes,
        {canonical_id: admission["proof_sha256"] for canonical_id, admission in admissions.items()},
    )
    grid = require_object(request.get("grid"), "grid")
    require_exact_keys(grid, {"columns", "order"}, "grid")
    columns = require_positive_int(grid.get("columns"), "grid.columns")
    if columns > frame_count:
        raise ContractError("grid.columns cannot exceed contract.frame_count")
    order = grid.get("order")
    if order not in ("row-major", "column-major"):
        raise ContractError("grid.order must be row-major or column-major")
    return ProductionModel(
        schema_version=request["schema_version"],
        contract=dict(contract),
        frame_width=frame_width,
        frame_height=frame_height,
        frame_count=frame_count,
        high_resolution_size=expected_high_resolution_size,
        animation_origin=animation_origin,
        anchor=anchor,
        safe_bounds=safe_bounds,
        canonical_ids=list(canonical),
        images=images,
        paths=paths,
        hashes=hashes,
        artifact_bytes=artifact_bytes,
        admissions=admissions,
        clips=clips,
        frame_ids=frame_ids,
        reviews=reviews,
        columns=columns,
        order=order,
    )
