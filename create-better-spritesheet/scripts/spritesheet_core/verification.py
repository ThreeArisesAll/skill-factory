"""Structured package verification and compatibility text rendering."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .admission import canonical_admission_proof
from .errors import ContractError
from .package_io import ResourceBudget, cell_position, read_regular_file_snapshot
from .protocol import (
    ADMISSION_PROOF_SCHEMA,
    CLIP_KEYS,
    CONTRACT_KEYS,
    FORBIDDEN_TERMS,
    HIGH_RESOLUTION_SHORT_SIDE,
    IDENTITY_ALGORITHM,
    MAX_CANONICAL_REFERENCES,
    MAX_CLIPS,
    MAX_FRAME_COUNT,
    MAX_JSON_FILE_BYTES,
    MAX_REVIEWS,
    NORMALIZATION_ALGORITHM,
    OUTLINE_ALGORITHM,
    PACKAGE_SCHEMA,
    SAMPLER,
    normalize_clip_metadata,
    require_exact_keys,
    require_object,
    validate_bounds,
    validate_outline_contract,
    validate_point,
    validate_review_requests,
)
from .rendering import (
    MAX_HIGH_RESOLUTION_SIDE,
    MAX_TARGET_SIDE,
    apply_outline,
    clear_transparent_rgb,
    normalize_low_alpha,
    normalize_to_canvas,
    open_rgba_snapshot,
    render_high_resolution_source,
    rendering_frame_record,
    rendering_receipt,
    resolve_high_resolution_dimensions,
)


@dataclass(frozen=True)
class VerificationReport:
    """Machine failures plus declared and reviewed compatibility messages."""

    failures: tuple[str, ...]
    declarations: tuple[str, ...]
    reviewed: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def lines(self) -> tuple[str, ...]:
        lines = list(self.failures)
        if self.passed:
            lines.append(
                "PASS MACHINE-VERIFIED rendering: each cell exactly equals deterministic "
                "high-resolution outline-or-identity and target-size replay",
            )
        lines.extend(self.declarations)
        lines.extend(self.reviewed)
        lines.append(f"machine_failures={len(self.failures)}")
        return tuple(lines)
def verify_package_report(manifest_path: Path) -> VerificationReport:
    budget = ResourceBudget()
    failures: list[str] = []
    declarations: list[str] = []
    reviewed: list[str] = []

    def check(condition: bool, location: str, detail: str) -> None:
        if not condition:
            failures.append(f"FAIL MACHINE-VERIFIED {location}: {detail}")

    check(manifest_path.name == "manifest.json", "manifest.path", "authoritative manifest must be named manifest.json")

    try:
        manifest_snapshot = read_regular_file_snapshot(
            manifest_path,
            "manifest",
            MAX_JSON_FILE_BYTES,
            budget=budget,
        )
        raw_text = manifest_snapshot.data.decode("utf-8")
        data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ContractError) as error:
        failures.append(f"FAIL MACHINE-VERIFIED manifest: cannot read JSON: {error}")
        data = {}
        raw_text = ""
    check(isinstance(data, dict), "$", "manifest must be an object")
    if not isinstance(data, dict):
        data = {}
    check(data.get("schema_version") == PACKAGE_SCHEMA, "schema_version", f"required={PACKAGE_SCHEMA!r}")
    check(
        set(data) == {"schema_version", "contract", "artifacts", "canonical_admissions", "clips", "reviews", "rendering", "assembly"},
        "$ fields",
        "manifest top-level fields are closed",
    )
    for term in FORBIDDEN_TERMS:
        check(term not in raw_text.lower(), "vocabulary", f"forbidden term={term!r}")
    base_dir = manifest_path.parent
    contract = data.get("contract") if isinstance(data.get("contract"), dict) else {}
    width = contract.get("frame_width")
    height = contract.get("frame_height")
    count = contract.get("frame_count")
    dimensions_valid = (
        isinstance(width, int)
        and not isinstance(width, bool)
        and isinstance(height, int)
        and not isinstance(height, bool)
        and min(width, height) > 0
        and min(width, height) < HIGH_RESOLUTION_SHORT_SIDE
        and max(width, height) <= MAX_TARGET_SIDE
        and isinstance(count, int)
        and not isinstance(count, bool)
        and 0 < count <= MAX_FRAME_COUNT
    )
    check(dimensions_valid, "contract.dimensions", "positive target dimensions must have shortest side below 512")
    check(contract.get("high_resolution_short_side") == 512, "contract.high_resolution_short_side", "required=512")
    check(contract.get("sampler") == SAMPLER, "contract.sampler", f"required={SAMPLER}")
    check(set(contract) == CONTRACT_KEYS, "contract.fields", f"required={sorted(CONTRACT_KEYS)}")
    normalized_outline: dict[str, Any] | None = None
    try:
        normalized_outline = validate_outline_contract(contract.get("outline"), "contract.outline")
        if (
            dimensions_valid
            and normalized_outline["enabled"]
            and normalized_outline["target_width"] >= min(width, height)
        ):
            raise ContractError("contract.outline.target_width must be smaller than the target shortest side")
        validate_point(contract.get("animation_origin"), "contract.animation_origin")
        anchor = validate_point(contract.get("anchor"), "contract.anchor")
        if not dimensions_valid or not (0 <= anchor[0] < width and 0 <= anchor[1] < height):
            raise ContractError("contract.anchor must be inside the target cell")
        validate_bounds(contract.get("safe_bounds"), "contract.safe_bounds", width, height)
    except (ContractError, TypeError) as error:
        check(False, "contract.runtime", str(error))
    artifacts_value = data.get("artifacts")
    check(isinstance(artifacts_value, list), "artifacts", "must be an array")
    if isinstance(artifacts_value, list) and len(artifacts_value) > (
        MAX_FRAME_COUNT + MAX_CANONICAL_REFERENCES + 1
    ):
        check(False, "artifacts", "exceeds bounded artifact count")
        artifacts_value = []
    artifacts: dict[str, dict[str, Any]] = {}
    images: dict[str, Image.Image] = {}
    artifact_relative_paths: set[str] = set()
    package_root = base_dir.resolve()
    allowed_types = {"canonical-reference", "high-resolution-frame-source", "spritesheet"}
    if isinstance(artifacts_value, list):
        for index, raw in enumerate(artifacts_value):
            location = f"artifacts[{index}]"
            if not isinstance(raw, dict):
                check(False, location, "must be an object")
                continue
            artifact_id = raw.get("id")
            valid_id = isinstance(artifact_id, str) and bool(artifact_id) and artifact_id not in artifacts
            check(valid_id, f"{location}.id", "must be a unique non-empty string")
            if not valid_id:
                continue
            artifacts[artifact_id] = raw
            artifact_type = raw.get("type")
            check(
                isinstance(artifact_type, str) and artifact_type in allowed_types,
                f"{location}.type",
                f"allowed={sorted(allowed_types)}",
            )
            path_value = raw.get("path")
            raw_path = Path(path_value) if isinstance(path_value, str) else Path("__invalid__")
            portable_relative = (
                isinstance(path_value, str)
                and bool(path_value)
                and not raw_path.is_absolute()
                and ".." not in raw_path.parts
                and path_value == raw_path.as_posix()
            )
            unresolved_path = base_dir / raw_path
            path = unresolved_path.resolve()
            contained = portable_relative and path.is_relative_to(package_root)
            check(contained, f"{location}.path", "must be a normalized package-relative path inside package root")
            expected_path = (
                "spritesheet.png"
                if artifact_type == "spritesheet"
                else f"artifacts/{raw.get('sha256')}.png"
            )
            check(
                path_value == expected_path,
                f"{location}.content-address",
                f"required={expected_path!r}",
            )
            check(contained and path.is_file(), f"{location}.path", f"file exists={contained and path.is_file()}")
            if not contained or not path.is_file():
                continue
            artifact_relative_paths.add(path_value)
            try:
                image, image_snapshot = open_rgba_snapshot(
                    unresolved_path,
                    f"{location}.path",
                    budget=budget,
                )
            except ContractError as error:
                check(False, f"{location}.image", str(error))
                continue
            check(
                image_snapshot.sha256 == raw.get("sha256"),
                f"{location}.sha256",
                "file content must match manifest",
            )
            images[artifact_id] = image
            base_artifact_keys = {"id", "type", "path", "sha256", "width", "height", "mode"}
            expected_artifact_keys = base_artifact_keys
            if artifact_type == "high-resolution-frame-source":
                expected_artifact_keys = base_artifact_keys | {"role", "canonical_reference"}
                if raw.get("role") == "in-between":
                    expected_artifact_keys |= {"previous_keyframe", "next_keyframe"}
            check(
                set(raw) == expected_artifact_keys,
                f"{location}.fields",
                f"required={sorted(expected_artifact_keys)}",
            )
            check(
                raw.get("width") == image.width
                and raw.get("height") == image.height
                and raw.get("mode") == image.mode,
                f"{location}.image-metadata",
                "dimensions and mode must match the decoded RGBA image",
            )
            if dimensions_valid and artifact_type in ("canonical-reference", "high-resolution-frame-source"):
                try:
                    expected_high_resolution_size, _ = resolve_high_resolution_dimensions(width, height)
                except (ValueError, OverflowError) as error:
                    check(False, f"{location}.high-resolution-canvas", str(error))
                else:
                    check(
                        image.size == expected_high_resolution_size,
                        f"{location}.high-resolution-canvas",
                        f"actual={image.size}, expected={expected_high_resolution_size}",
                    )
    admission_hashes: dict[str, str] = {}
    admission_relative_paths: set[str] = set()
    admissions_value = data.get("canonical_admissions")
    check(isinstance(admissions_value, list) and bool(admissions_value), "canonical_admissions", "must be a non-empty array")
    if isinstance(admissions_value, list) and len(admissions_value) > MAX_CANONICAL_REFERENCES:
        check(False, "canonical_admissions", "exceeds bounded canonical admission count")
        admissions_value = []
    if isinstance(admissions_value, list):
        for index, raw_admission in enumerate(admissions_value):
            location = f"canonical_admissions[{index}]"
            if not isinstance(raw_admission, dict):
                check(False, location, "must be an object")
                continue
            check(
                set(raw_admission) == {
                    "canonical_reference", "proof_path", "proof_sha256",
                    "source_path", "source_sha256", "evidence_path", "evidence_sha256",
                },
                f"{location}.fields",
                "admission record fields are closed",
            )
            canonical_id = raw_admission.get("canonical_reference")
            proof_hash = raw_admission.get("proof_sha256")
            source_hash = raw_admission.get("source_sha256")
            evidence_hash = raw_admission.get("evidence_sha256")
            proof_value = raw_admission.get("proof_path")
            source_value = raw_admission.get("source_path")
            evidence_value = raw_admission.get("evidence_path")
            proof_expected = f"admission/{proof_hash}.json"
            source_expected = f"evidence/{source_hash}.png"
            evidence_expected = f"evidence/{evidence_hash}.json"
            valid_paths = (
                proof_value == proof_expected
                and source_value == source_expected
                and evidence_value == evidence_expected
            )
            check(valid_paths, f"{location}.content-address", "proof and source paths must be content-addressed")
            proof_input = base_dir / proof_value if isinstance(proof_value, str) else base_dir
            source_input = base_dir / source_value if isinstance(source_value, str) else base_dir
            evidence_input = base_dir / evidence_value if isinstance(evidence_value, str) else base_dir
            proof_path = proof_input.resolve()
            source_path = source_input.resolve()
            evidence_path = evidence_input.resolve()
            contained = (
                valid_paths
                and proof_path.is_relative_to(package_root)
                and source_path.is_relative_to(package_root)
                and evidence_path.is_relative_to(package_root)
                and proof_path.is_file()
                and source_path.is_file()
                and evidence_path.is_file()
                and not proof_path.is_symlink()
                and not source_path.is_symlink()
                and not evidence_path.is_symlink()
            )
            check(contained, f"{location}.files", "proof and source must be regular files inside package root")
            if not contained or not isinstance(canonical_id, str):
                continue
            admission_relative_paths.update((proof_value, source_value, evidence_value))
            try:
                proof_snapshot = read_regular_file_snapshot(
                    proof_input,
                    "admission proof",
                    MAX_JSON_FILE_BYTES,
                    budget=budget,
                )
                evidence_snapshot = read_regular_file_snapshot(
                    evidence_input,
                    "canonical evidence",
                    MAX_JSON_FILE_BYTES,
                    budget=budget,
                )
                source, source_snapshot = open_rgba_snapshot(
                    source_input,
                    "admission source",
                    budget=budget,
                )
            except ContractError as error:
                check(False, f"{location}.files", str(error))
                continue
            actual_proof_hash = proof_snapshot.sha256
            actual_source_hash = source_snapshot.sha256
            actual_evidence_hash = evidence_snapshot.sha256
            check(actual_proof_hash == proof_hash, f"{location}.proof_sha256", "proof bytes must match")
            check(actual_source_hash == source_hash, f"{location}.source_sha256", "source bytes must match")
            check(actual_evidence_hash == evidence_hash, f"{location}.evidence_sha256", "evidence bytes must match")
            try:
                proof = require_object(json.loads(proof_snapshot.data), "admission proof")
                current_proof_keys = {
                    "schema_version", "canonical_reference", "target", "source", "outline",
                    "derivation", "authoring_evidence_sha256", "alpha_policy", "review_previews",
                }
                require_exact_keys(proof, current_proof_keys, "admission proof")
                missing_proof_fields = sorted(current_proof_keys - set(proof))
                if missing_proof_fields:
                    raise ContractError(
                        "admission proof is missing required fields: "
                        + ", ".join(missing_proof_fields),
                    )
                if proof.get("schema_version") != ADMISSION_PROOF_SCHEMA:
                    raise ContractError(f"admission proof schema_version must be {ADMISSION_PROOF_SCHEMA!r}")
                canonical_record = require_object(proof.get("canonical_reference"), "admission proof.canonical_reference")
                require_exact_keys(
                    canonical_record,
                    {"id", "sha256", "width", "height", "mode"},
                    "admission proof.canonical_reference",
                )
                derivation = require_object(proof.get("derivation"), "admission proof.derivation")
                require_exact_keys(derivation, {"normalization", "outline"}, "admission proof.derivation")
                raw_proof_outline = require_object(proof.get("outline"), "admission proof.outline")
                resolved_width = raw_proof_outline.get("resolved_high_resolution_width")
                proof_outline = validate_outline_contract(
                    {key: value for key, value in raw_proof_outline.items() if key != "resolved_high_resolution_width"},
                    "admission proof.outline",
                )
                expected_resolved = (
                    round(proof_outline["target_width"] * HIGH_RESOLUTION_SHORT_SIDE / min(width, height))
                    if proof_outline["enabled"] and dimensions_valid
                    else 0
                )
                if resolved_width != expected_resolved:
                    raise ContractError("admission proof resolved outline width is invalid")
                if proof.get("target") != {"frame_width": width, "frame_height": height}:
                    raise ContractError("admission proof target must match package contract")
                if proof.get("outline") != contract.get("outline") | {"resolved_high_resolution_width": expected_resolved}:
                    raise ContractError("admission proof outline must match package contract")
                expected_derivation = {
                    "normalization": NORMALIZATION_ALGORITHM,
                    "outline": OUTLINE_ALGORITHM if proof_outline["enabled"] else IDENTITY_ALGORITHM,
                }
                if derivation != expected_derivation:
                    raise ContractError("admission proof algorithms are invalid")
                if proof.get("authoring_evidence_sha256") != actual_evidence_hash:
                    raise ContractError("admission proof must bind the packaged authoring evidence")
                source_record = require_object(proof.get("source"), "admission proof.source")
                require_exact_keys(source_record, {"sha256", "width", "height", "mode"}, "admission proof.source")
                if source_record != {
                    "sha256": actual_source_hash,
                    "width": source.width,
                    "height": source.height,
                    "mode": source.mode,
                }:
                    raise ContractError("admission source metadata is invalid")
                expected_size, _ = resolve_high_resolution_dimensions(width, height)
                normalized_source = normalize_to_canvas(source, expected_size)
                normalized = normalize_low_alpha(normalized_source)
                canonical_image = images.get(canonical_id)
                canonical_artifact = artifacts.get(canonical_id, {})
                if (
                    canonical_image is None
                    or canonical_artifact.get("type") != "canonical-reference"
                    or canonical_record != {
                        "id": canonical_id,
                        "sha256": canonical_artifact.get("sha256"),
                        "width": canonical_image.width,
                        "height": canonical_image.height,
                        "mode": canonical_image.mode,
                    }
                ):
                    raise ContractError("admission proof must bind a current canonical-reference artifact")
                replay = normalized
                if proof_outline["enabled"]:
                    replay, _ = apply_outline(
                        normalized,
                        proof_outline["target_width"],
                        min(width, height),
                        proof_outline["color"],
                    )
                if replay.tobytes() != canonical_image.tobytes():
                    raise ContractError("canonical reference does not pixel-match packaged admission evidence")
                canonical_path = base_dir / canonical_artifact["path"]
                replayed_proof = canonical_admission_proof(
                    canonical_id,
                    canonical_path,
                    evidence_input,
                    base_dir,
                    proof_outline,
                    width,
                    height,
                    budget=budget,
                    require_review_preview_files=False,
                )
                replayed_payload = {
                    key: value for key, value in replayed_proof.items() if not key.startswith("_")
                }
                if proof != replayed_payload:
                    raise ContractError("admission proof must exactly match independent evidence replay")
            except (
                ContractError,
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                TypeError,
            ) as error:
                check(False, location, str(error))
            else:
                if canonical_id in admission_hashes:
                    check(False, f"{location}.canonical_reference", "must be unique")
                admission_hashes[canonical_id] = actual_proof_hash
    clips_value = data.get("clips")
    check(isinstance(clips_value, list) and bool(clips_value), "clips", "must be a non-empty array")
    if isinstance(clips_value, list) and len(clips_value) > MAX_CLIPS:
        check(False, "clips", "exceeds bounded clip count")
        clips_value = []
    frame_ids: list[str] = []
    canonical_ids: list[str] = []
    expected_sources: list[tuple[str, bool]] = []
    clip_review_scopes: list[tuple[str, list[str]]] = []
    clip_ids_seen: set[str] = set()
    if isinstance(clips_value, list):
        for clip_index, raw_clip in enumerate(clips_value):
            if not isinstance(raw_clip, dict):
                check(False, f"clips[{clip_index}]", "must be an object")
                continue
            check(
                set(raw_clip) == (CLIP_KEYS - {"frames"}) | {"frame_ids"},
                f"clips[{clip_index}].fields",
                "clip fields are closed",
            )
            clip_id = raw_clip.get("id")
            valid_clip_id = isinstance(clip_id, str) and bool(clip_id) and clip_id not in clip_ids_seen
            check(valid_clip_id, f"clips[{clip_index}].id", "must be a unique non-empty string")
            if isinstance(clip_id, str):
                clip_ids_seen.add(clip_id)
            canonical_id = raw_clip.get("canonical_reference")
            canonical_ids.append(canonical_id) if isinstance(canonical_id, str) else None
            check(
                isinstance(canonical_id, str)
                and canonical_id in artifacts
                and artifacts.get(canonical_id, {}).get("type") == "canonical-reference",
                f"clips[{clip_index}].canonical_reference",
                "must reference a canonical-reference artifact",
            )
            loop = raw_clip.get("loop")
            repeat = raw_clip.get("repeat_opening_cell")
            check(isinstance(loop, bool) and isinstance(repeat, bool), f"clips[{clip_index}].loop", "flags must be boolean")
            check(not repeat or loop is True, f"clips[{clip_index}].repeat_opening_cell", "allowed only for loops")
            clip_frame_ids = raw_clip.get("frame_ids")
            if not isinstance(clip_frame_ids, list):
                check(False, f"clips[{clip_index}].frame_ids", "must be an array")
                continue
            try:
                metadata_clip = {
                    key: value
                    for key, value in raw_clip.items()
                    if key != "frame_ids"
                }
                metadata_clip["frames"] = []
                normalize_clip_metadata(
                    metadata_clip,
                    clip_id if isinstance(clip_id, str) else f"clip-{clip_index}",
                    len(clip_frame_ids) + int(repeat is True),
                    width if isinstance(width, int) else 0,
                    height if isinstance(height, int) else 0,
                )
            except (ContractError, TypeError) as error:
                check(False, f"clips[{clip_index}].runtime", str(error))
            frames = [
                artifacts.get(frame_id, {})
                if isinstance(frame_id, str)
                else {}
                for frame_id in clip_frame_ids
            ]
            local_keyframes = [
                index
                for index, frame in enumerate(frames)
                if isinstance(frame, dict) and frame.get("role") == "keyframe"
            ]
            in_between_count = sum(
                isinstance(frame, dict) and frame.get("role") == "in-between"
                for frame in frames
            )
            check(len(local_keyframes) >= 2, f"clips[{clip_index}].keyframes", "requires at least two")
            check(in_between_count >= 2, f"clips[{clip_index}].in-betweens", "requires at least two")
            for frame_index, frame in enumerate(frames):
                if not isinstance(frame, dict):
                    check(False, f"clips[{clip_index}].frames[{frame_index}]", "must be an object")
                    continue
                frame_id = frame.get("id")
                role = frame.get("role")
                check(role in ("keyframe", "in-between"), f"frame[{frame_id}].role", "invalid role")
                check(
                    isinstance(frame_id, str)
                    and frame_id in artifacts
                    and artifacts[frame_id].get("type") == "high-resolution-frame-source"
                    and artifacts[frame_id].get("role") == role,
                    f"frame[{frame_id}].artifact",
                    "must reference a matching high-resolution-frame-source artifact",
                )
                check(
                    frame.get("canonical_reference") == canonical_id,
                    f"frame[{frame_id}].canonical_reference",
                    "must bind the clip canonical reference",
                )
                if not isinstance(frame_id, str):
                    continue
                frame_ids.append(frame_id)
                expected_sources.append((frame_id, False))
                if role == "keyframe":
                    check(
                        "previous_keyframe" not in frame and "next_keyframe" not in frame,
                        f"frame[{frame_id}].brackets",
                        "keyframes cannot declare brackets",
                    )
                elif role == "in-between":
                    previous = [index for index in local_keyframes if index < frame_index]
                    following = [index for index in local_keyframes if index > frame_index]
                    previous_index = previous[-1] if previous else (local_keyframes[-1] if loop else None)
                    following_index = following[0] if following else (local_keyframes[0] if loop else None)
                    bracket_valid = (
                        previous_index is not None
                        and following_index is not None
                        and frame.get("previous_keyframe") == frames[previous_index].get("id")
                        and frame.get("next_keyframe") == frames[following_index].get("id")
                    )
                    check(bool(bracket_valid), f"frame[{frame_id}].bracketing", "must name adjacent keyframes")
            clip_frame_ids_for_review = [
                frame.get("id")
                for frame in frames
                if isinstance(frame.get("id"), str)
            ]
            clip_review_scopes.extend(
                (
                    (
                        "keyframe-set-approval",
                        [canonical_id, *[
                            frame.get("id")
                            for frame in frames
                            if frame.get("role") == "keyframe" and isinstance(frame.get("id"), str)
                        ]],
                    ),
                    ("sequence-approval", [canonical_id, *clip_frame_ids_for_review]),
                ),
            )
            if repeat and clip_frame_ids and isinstance(clip_frame_ids[0], str):
                expected_sources.append((clip_frame_ids[0], True))
    declared_canonical_ids = [
        artifact_id
        for artifact_id, artifact in artifacts.items()
        if artifact.get("type") == "canonical-reference"
    ]
    check(
        set(admission_hashes) == set(declared_canonical_ids),
        "canonical_admissions.graph",
        "every canonical reference must have exactly one valid admission proof",
    )
    check(
        set(canonical_ids) == set(declared_canonical_ids),
        "clips.canonical_reference",
        "every canonical reference must be consumed by at least one clip",
    )
    check(len(frame_ids) == len(set(frame_ids)), "clips.frames", "frame IDs must be unique")
    frame_pixel_hashes = [
        hashlib.sha256(images[frame_id].tobytes()).hexdigest()
        for frame_id in frame_ids
        if frame_id in images
    ]
    check(
        len(frame_pixel_hashes) == len(frame_ids) and len(set(frame_pixel_hashes)) == len(frame_pixel_hashes),
        "high-resolution-frame-source.pixels",
        "all high-resolution frame sources must have distinct pixels",
    )
    for canonical_id in set(canonical_ids):
        if canonical_id in images:
            canonical_pixels = hashlib.sha256(images[canonical_id].tobytes()).hexdigest()
            check(canonical_pixels not in set(frame_pixel_hashes), f"canonical-reference[{canonical_id}].pixels", "must differ from every frame")
    canonical_pixel_hashes = [
        hashlib.sha256(images[canonical_id].tobytes()).hexdigest()
        for canonical_id in declared_canonical_ids
        if canonical_id in images
    ]
    check(
        len(canonical_pixel_hashes) == len(declared_canonical_ids)
        and len(set(canonical_pixel_hashes)) == len(canonical_pixel_hashes),
        "canonical-reference.pixels",
        "canonical references must have distinct pixels; shared content must use one artifact ID",
    )
    reviews_value = data.get("reviews")
    if isinstance(reviews_value, list) and len(reviews_value) > MAX_REVIEWS:
        check(False, "reviews", "exceeds bounded review count")
        reviews_value = []
    hashes = {artifact_id: artifact.get("sha256") for artifact_id, artifact in artifacts.items()}
    expected_reviews = [
        *[("canonical-approval", [canonical_id]) for canonical_id in declared_canonical_ids],
        *clip_review_scopes,
    ]
    try:
        validated_reviews = validate_review_requests(reviews_value, expected_reviews, hashes, admission_hashes)
    except (ContractError, KeyError, TypeError) as error:
        check(False, "reviews", str(error))
    else:
        reviewed.extend(
            f"INFO REVIEWED {review['gate']}: reviewer={review['reviewer']}; evidence={review['evidence']}"
            for review in validated_reviews
        )
    assembly = data.get("assembly") if isinstance(data.get("assembly"), dict) else {}
    check(
        set(assembly) == {"sheet", "columns", "rows", "order", "cells"},
        "assembly.fields",
        "assembly fields are closed",
    )
    columns = assembly.get("columns")
    rows = assembly.get("rows")
    order = assembly.get("order")
    cells = assembly.get("cells")
    if isinstance(cells, list) and len(cells) > MAX_FRAME_COUNT:
        check(False, "assembly.cells", "exceeds bounded cell count")
        cells = []
    layout_valid = (
        isinstance(columns, int)
        and not isinstance(columns, bool)
        and columns > 0
        and isinstance(count, int)
        and not isinstance(count, bool)
        and columns <= count
        and isinstance(rows, int)
        and not isinstance(rows, bool)
        and rows > 0
        and order in ("row-major", "column-major")
        and isinstance(cells, list)
        and rows == (count + columns - 1) // columns
        and cells == [
            {
                "source": source,
                "repeated_opening": repeated,
                "index": index,
                "column": cell_position(index, columns, rows, order)[0],
                "row": cell_position(index, columns, rows, order)[1],
            }
            for index, (source, repeated) in enumerate(expected_sources)
        ]
    )
    check(layout_valid, "assembly.cells", "cells must exactly follow clip order and grid order")
    check(isinstance(count, int) and count == len(expected_sources), "contract.frame_count", "must equal assembled cell count")
    sheet_id = assembly.get("sheet")
    check(
        sheet_id == "spritesheet"
        and artifacts.get("spritesheet", {}).get("type") == "spritesheet",
        "assembly.sheet",
        "must reference the reserved spritesheet artifact ID and type",
    )
    sheet = images.get(sheet_id) if isinstance(sheet_id, str) else None
    replayed_cells: dict[str, Image.Image] = {}
    receipt_frames: list[dict[str, Any]] = []
    resolved_outline_width: int | None = None
    rendering_replay_valid = normalized_outline is not None and dimensions_valid
    if rendering_replay_valid:
        for frame_id in frame_ids:
            source = images.get(frame_id)
            artifact = artifacts.get(frame_id, {})
            if source is None:
                rendering_replay_valid = False
                continue
            try:
                outlined, cell, frame_outline_width = render_high_resolution_source(
                    source,
                    normalized_outline,
                    (width, height),
                )
            except ContractError as error:
                check(False, f"rendering.frames[{frame_id}]", str(error))
                rendering_replay_valid = False
                continue
            if resolved_outline_width is None:
                resolved_outline_width = frame_outline_width
            elif resolved_outline_width != frame_outline_width:
                check(False, "rendering.resolved_high_resolution_outline_width", "must be consistent")
                rendering_replay_valid = False
            replayed_cells[frame_id] = cell
            receipt_frames.append(
                rendering_frame_record(frame_id, artifact.get("sha256"), outlined, cell),
            )
    replay_safe = (
        dimensions_valid
        and layout_valid
        and count == len(expected_sources)
        and isinstance(columns, int)
        and isinstance(rows, int)
        and columns * width <= MAX_HIGH_RESOLUTION_SIDE
        and rows * height <= MAX_HIGH_RESOLUTION_SIDE
    )
    check(replay_safe, "assembly.safe-dimensions", "sheet dimensions must be bounded for deterministic replay")
    replayed_sheet: Image.Image | None = None
    if replay_safe and sheet is not None:
        check(sheet.size == (columns * width, rows * height), "assembly.sheet.dimensions", "must match the fixed grid")
        pixel_match = True
        used: set[tuple[int, int]] = set()
        replayed_sheet = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
        if isinstance(cells, list):
            for index, (source, _) in enumerate(expected_sources):
                column, row = cell_position(index, columns, rows, order)
                used.add((column, row))
                if source not in replayed_cells:
                    pixel_match = False
                    continue
                replayed_sheet.alpha_composite(replayed_cells[source], (column * width, row * height))
                expected = replayed_cells[source].tobytes()
                actual = sheet.crop(
                    (column * width, row * height, (column + 1) * width, (row + 1) * height),
                ).tobytes()
                pixel_match = pixel_match and actual == expected
        check(
            pixel_match,
            "cells",
            "each cell must exactly equal the recorded algorithm applied directly to its unique high-resolution source",
        )
        replayed_sheet = clear_transparent_rgb(replayed_sheet)
        check(
            sheet.tobytes() == replayed_sheet.tobytes(),
            "sheet.replay",
            "sheet RGBA pixels must exactly match deterministic full-sheet replay",
        )
        unused_empty = True
        for row in range(rows):
            for column in range(columns):
                if (column, row) in used:
                    continue
                unused = sheet.crop(
                    (column * width, row * height, (column + 1) * width, (row + 1) * height),
                )
                unused_empty = unused_empty and unused.getchannel("A").getextrema() == (0, 0)
        check(unused_empty, "assembly.unused-cells", "unused cell alpha must be zero")
    else:
        check(False, "assembly.sheet", "sheet or layout is unavailable")
    rendering = data.get("rendering") if isinstance(data.get("rendering"), dict) else {}
    expected_rendering = rendering_receipt(
        normalized_outline,
        resolved_outline_width or 0,
        receipt_frames,
        (
            hashlib.sha256(replayed_sheet.tobytes()).hexdigest()
            if replayed_sheet is not None
            else None
        ),
    )
    check(
        rendering_replay_valid and rendering == expected_rendering,
        "rendering",
        "receipt must exactly match independent outline, resize, and sheet replay",
    )
    referenced = set(frame_ids) | set(canonical_ids)
    if isinstance(sheet_id, str):
        referenced.add(sheet_id)
    check(set(artifacts) == referenced, "artifacts.graph", "every artifact must be referenced and no artifact may be orphaned")
    package_entries = list(base_dir.rglob("*"))
    actual_package_entries = {
        path.relative_to(base_dir).as_posix()
        for path in package_entries
    }
    expected_package_entries = artifact_relative_paths | admission_relative_paths | {
        "manifest.json",
        "artifacts",
        "admission",
        "evidence",
    }
    check(
        actual_package_entries == expected_package_entries
        and all(not path.is_symlink() for path in package_entries),
        "package.files",
        "package must contain only regular declared files and the artifacts directory, with no symlinks",
    )
    declarations.append(
        "INFO DECLARED generation: canonical references are declared visual references and in-between brackets are declared creative relationships",
    )
    return VerificationReport(tuple(failures), tuple(declarations), tuple(reviewed))


def verify_package(manifest_path: Path, *, emit: bool = True) -> bool:
    """Render the legacy verification text and return its stable boolean result."""
    report = verify_package_report(manifest_path)
    if emit:
        for line in report.lines():
            print(line)
    return report.passed
