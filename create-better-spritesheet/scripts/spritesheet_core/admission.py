"""Canonical admission replay and proof construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import ContractError
from .package_io import ResourceBudget, read_regular_file_snapshot
from .protocol import (
    ADMISSION_PROOF_SCHEMA,
    EVIDENCE_SCHEMA,
    HIGH_RESOLUTION_SHORT_SIDE,
    IDENTITY_ALGORITHM,
    MAX_JSON_FILE_BYTES,
    NORMALIZATION_ALGORITHM,
    OUTLINE_ALGORITHM,
    require_exact_keys,
    require_object,
    require_string,
)
from .rendering import (
    MAX_PNG_FILE_BYTES,
    alpha_policy_record,
    apply_outline,
    decode_rgba,
    normalize_low_alpha,
    normalize_to_canvas,
    open_rgba_snapshot,
    resolve_high_resolution_dimensions,
    review_preview_payloads,
)


def canonical_admission_proof(
    canonical_id: str,
    canonical_path: Path,
    evidence_path: Path,
    evidence_root: Path,
    contract_outline: dict[str, Any],
    frame_width: int,
    frame_height: int,
    *,
    budget: ResourceBudget | None = None,
    require_review_preview_files: bool = True,
) -> dict[str, Any]:
    try:
        evidence_snapshot = read_regular_file_snapshot(
            evidence_path,
            "canonical evidence",
            MAX_JSON_FILE_BYTES,
            budget=budget,
        )
        evidence = require_object(json.loads(evidence_snapshot.data), "canonical evidence")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read canonical evidence: {error}") from error
    current_evidence_keys = {
        "schema_version", "candidate", "source", "target", "derivation", "outline", "metrics",
        "alpha_policy", "review_previews",
    }
    require_exact_keys(evidence, current_evidence_keys, "canonical evidence")
    missing = sorted(current_evidence_keys - set(evidence))
    if missing:
        raise ContractError("canonical evidence is missing required fields: " + ", ".join(missing))
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        raise ContractError(f"canonical evidence schema_version must be {EVIDENCE_SCHEMA!r}")
    candidate = require_object(evidence.get("candidate"), "canonical evidence.candidate")
    require_exact_keys(candidate, {"kind", "path", "sha256", "width", "height", "mode"}, "canonical evidence.candidate")
    canonical, canonical_snapshot = open_rgba_snapshot(
        canonical_path,
        f"canonical reference {canonical_id!r}",
        budget=budget,
    )
    canonical_hash = canonical_snapshot.sha256
    if (
        candidate.get("kind") != "canonical-reference-candidate"
        or candidate.get("path") != "canonical-reference-candidate.png"
        or candidate.get("sha256") != canonical_hash
        or candidate.get("width") != canonical.width
        or candidate.get("height") != canonical.height
        or candidate.get("mode") != "RGBA"
    ):
        raise ContractError(f"canonical reference {canonical_id!r} does not match its evidence candidate")
    target = require_object(evidence.get("target"), "canonical evidence.target")
    require_exact_keys(target, {"frame_width", "frame_height"}, "canonical evidence.target")
    if target != {"frame_width": frame_width, "frame_height": frame_height}:
        raise ContractError(f"canonical reference {canonical_id!r} evidence target does not match production contract")
    source_record = require_object(evidence.get("source"), "canonical evidence.source")
    require_exact_keys(source_record, {"path", "sha256"}, "canonical evidence.source")
    source_value = require_string(source_record.get("path"), "canonical evidence.source.path")
    source_relative = Path(source_value)
    source_input = evidence_root / source_relative
    source_path = source_input.resolve()
    if (
        source_relative.is_absolute()
        or ".." in source_relative.parts
        or source_value != source_relative.as_posix()
        or source_value != f"evidence/{source_record.get('sha256')}.png"
        or not source_path.is_relative_to(evidence_root.resolve())
    ):
        raise ContractError(f"canonical reference {canonical_id!r} source hash does not match evidence")
    source, source_snapshot = open_rgba_snapshot(
        source_input,
        "canonical evidence source",
        budget=budget,
    )
    if source_snapshot.sha256 != source_record.get("sha256"):
        raise ContractError(f"canonical reference {canonical_id!r} source hash does not match evidence")
    expected_size, _ = resolve_high_resolution_dimensions(frame_width, frame_height)
    normalized_source = normalize_to_canvas(source, expected_size)
    normalized = normalize_low_alpha(normalized_source)
    derivation = require_object(evidence.get("derivation"), "canonical evidence.derivation")
    require_exact_keys(derivation, {"normalization", "outline"}, "canonical evidence.derivation")
    expected_outline_algorithm = OUTLINE_ALGORITHM if contract_outline["enabled"] else IDENTITY_ALGORITHM
    if derivation != {"normalization": NORMALIZATION_ALGORITHM, "outline": expected_outline_algorithm}:
        raise ContractError("canonical evidence derivation algorithms do not match the production contract")
    outline = require_object(evidence.get("outline"), "canonical evidence.outline")
    expected_outline = {
        **contract_outline,
        "resolved_high_resolution_width": (
            round(contract_outline["target_width"] * HIGH_RESOLUTION_SHORT_SIDE / min(frame_width, frame_height))
            if contract_outline["enabled"]
            else 0
        ),
    }
    if outline != expected_outline:
        raise ContractError("canonical evidence outline does not exactly match the production outline contract")
    replay = normalized
    if contract_outline["enabled"]:
        replay, _ = apply_outline(
            normalized,
            contract_outline["target_width"],
            min(frame_width, frame_height),
            contract_outline["color"],
        )
    if replay.tobytes() != canonical.tobytes():
        raise ContractError("canonical reference does not pixel-match its replayed admission evidence")
    metrics = require_object(evidence.get("metrics"), "canonical evidence.metrics")
    require_exact_keys(metrics, {"width", "height", "short_side", "visible_bbox"}, "canonical evidence.metrics")
    visible_bbox = canonical.getchannel("A").getbbox()
    if metrics != {
        "width": canonical.width,
        "height": canonical.height,
        "short_side": min(canonical.size),
        "visible_bbox": list(visible_bbox) if visible_bbox is not None else None,
    }:
        raise ContractError("canonical evidence metrics must exactly match the candidate")
    alpha_policy_value = require_object(
        evidence.get("alpha_policy"),
        "canonical evidence.alpha_policy",
    )
    expected_alpha_policy = alpha_policy_record(
        normalized_source,
        canonical,
        contract_outline["enabled"],
    )
    if alpha_policy_value != expected_alpha_policy:
        raise ContractError("canonical evidence alpha_policy does not match replayed pixels")
    if expected_alpha_policy["status"] != "passed":
        raise ContractError("unbacked low-alpha boundary prevents canonical admission")
    raw_previews = evidence.get("review_previews")
    if not isinstance(raw_previews, list):
        raise ContractError("canonical evidence.review_previews must be an array")
    expected_payloads = review_preview_payloads(canonical, (frame_width, frame_height))
    expected_previews = [record for record, _ in expected_payloads]
    preview_keys = set(expected_previews[0])
    replayed_previews: list[dict[str, Any]] = []
    for index, raw_record in enumerate(raw_previews):
        record = require_object(
            raw_record,
            f"canonical evidence.review_previews[{index}]",
        )
        require_exact_keys(
            record,
            preview_keys,
            f"canonical evidence.review_previews[{index}]",
        )
        png_hash = record.get("sha256")
        if (
            not isinstance(png_hash, str)
            or len(png_hash) != 64
            or any(character not in "0123456789abcdef" for character in png_hash)
        ):
            raise ContractError(
                f"canonical evidence.review_previews[{index}].sha256 must be a lowercase SHA-256 digest"
            )
        replayed_previews.append({
            key: value
            for key, value in record.items()
            if key != "sha256"
        })
    expected_semantics = [
        {
            key: value
            for key, value in record.items()
            if key != "sha256"
        }
        for record in expected_previews
    ]
    if replayed_previews != expected_semantics:
        raise ContractError("canonical evidence review_previews do not match deterministic replay")
    preview_presence: list[bool] = []
    for raw_record, (expected_record, _) in zip(
        raw_previews,
        expected_payloads,
        strict=True,
    ):
        record = require_object(raw_record, "canonical evidence.review_previews entry")
        relative = Path(str(record["path"]))
        preview_path = evidence_root / relative
        resolved = preview_path.resolve()
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or str(record["path"]) != relative.as_posix()
            or not resolved.is_relative_to(evidence_root.resolve())
        ):
            raise ContractError("canonical review preview path escapes the evidence root")
        exists = preview_path.exists() or preview_path.is_symlink()
        preview_presence.append(exists)
        if not exists:
            continue
        snapshot = read_regular_file_snapshot(
            preview_path,
            "canonical review preview",
            MAX_PNG_FILE_BYTES,
            budget=budget,
        )
        preview = decode_rgba(
            snapshot.data,
            "canonical review preview",
            expected_size=(expected_record["width"], expected_record["height"]),
            budget=budget,
        )
        if snapshot.sha256 != record["sha256"]:
            raise ContractError("canonical review preview PNG hash does not match evidence")
        preview_rgba_hash = hashlib.sha256(preview.tobytes()).hexdigest()
        if (
            preview_rgba_hash != record["rgba_sha256"]
            or preview.width != record["width"]
            or preview.height != record["height"]
            or preview.mode != record["mode"]
            or preview_rgba_hash != expected_record["rgba_sha256"]
        ):
            raise ContractError("canonical review preview pixels do not match replay")
    if (require_review_preview_files and not all(preview_presence)) or (
        any(preview_presence) and not all(preview_presence)
    ):
        raise ContractError("canonical review preview matrix must be complete")
    proof = {
        "schema_version": ADMISSION_PROOF_SCHEMA,
        "canonical_reference": {
            "id": canonical_id,
            "sha256": canonical_hash,
            "width": canonical.width,
            "height": canonical.height,
            "mode": canonical.mode,
        },
        "target": dict(target),
        "source": {
            "sha256": source_record["sha256"],
            "width": source.width,
            "height": source.height,
            "mode": source.mode,
        },
        "outline": dict(outline),
        "derivation": dict(derivation),
        "authoring_evidence_sha256": evidence_snapshot.sha256,
        "_source_path": source_path,
        "_evidence_path": evidence_path,
        "_source_bytes": source_snapshot.data,
        "_evidence_bytes": evidence_snapshot.data,
    }
    proof["alpha_policy"] = dict(alpha_policy_value)
    proof["review_previews"] = [dict(record) for record in raw_previews]
    return proof
