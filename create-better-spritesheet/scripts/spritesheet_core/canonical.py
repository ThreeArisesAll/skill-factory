"""Canonical candidate preparation workflow."""

from __future__ import annotations

import json
from pathlib import Path

from .admission import canonical_admission_proof
from .errors import ContractError
from .package_io import (
    ResourceBudget,
    atomic_directory,
    read_regular_file_snapshot,
    sha256_file,
)
from .protocol import (
    CANONICAL_REQUEST_SCHEMA,
    EVIDENCE_SCHEMA,
    IDENTITY_ALGORITHM,
    NORMALIZATION_ALGORITHM,
    OUTLINE_ALGORITHM,
    read_request,
    require_exact_keys,
    require_object,
    require_positive_int,
    require_string,
    validate_outline_contract,
)
from .rendering import (
    apply_outline,
    decode_rgba,
    normalize_to_canvas,
    resolve_high_resolution_dimensions,
)


def prepare_canonical(request_path: Path, output_dir: Path) -> None:
    budget = ResourceBudget()
    request = read_request(request_path, CANONICAL_REQUEST_SCHEMA, budget=budget)
    require_exact_keys(request, {"schema_version", "canonical_id", "source", "target", "outline"}, "request")
    canonical_id = require_string(request.get("canonical_id"), "canonical_id")
    source_value = request.get("source")
    if not isinstance(source_value, str) or not source_value:
        raise ContractError("source must be a non-empty path string")
    source_path = Path(source_value)
    if not source_path.is_absolute():
        raise ContractError("source must be an absolute path")
    from .rendering import MAX_PNG_FILE_BYTES

    source_snapshot = read_regular_file_snapshot(
        source_path,
        "source",
        MAX_PNG_FILE_BYTES,
        budget=budget,
    )
    source_bytes = source_snapshot.data
    source = decode_rgba(source_bytes, "source")
    source_digest = source_snapshot.sha256
    target = require_object(request.get("target"), "target")
    require_exact_keys(target, {"frame_width", "frame_height"}, "target")
    frame_width = require_positive_int(target.get("frame_width"), "target.frame_width")
    frame_height = require_positive_int(target.get("frame_height"), "target.frame_height")
    canvas_size, _ = resolve_high_resolution_dimensions(frame_width, frame_height)
    candidate = normalize_to_canvas(source, canvas_size)
    outline = validate_outline_contract(request.get("outline"), "outline")
    enabled = outline["enabled"]
    resolved_width = 0
    if enabled:
        target_width = require_positive_int(outline.get("target_width"), "outline.target_width")
        if target_width >= min(frame_width, frame_height):
            raise ContractError("outline.target_width must be smaller than the target shortest side")
        color = outline["color"]
        candidate, resolved_width = apply_outline(
            candidate,
            target_width,
            min(frame_width, frame_height),
            color,
        )
    bbox = candidate.getchannel("A").getbbox()
    if bbox is None:
        raise ContractError("canonical candidate has no visible pixels")
    if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= candidate.width or bbox[3] >= candidate.height:
        raise ContractError("canonical candidate visible pixels must not touch or clip against the canvas border")

    def build(destination: Path) -> None:
        candidate_path = destination / "canonical-reference-candidate.png"
        candidate.save(candidate_path)
        source_relative = Path("evidence") / f"{source_digest}.png"
        source_evidence_path = destination / source_relative
        source_evidence_path.parent.mkdir()
        source_evidence_path.write_bytes(source_bytes)
        outline_evidence = {
            "enabled": enabled,
            "target_width": outline.get("target_width"),
            "resolved_high_resolution_width": resolved_width,
        }
        if enabled:
            outline_evidence["color"] = outline["color"]
        evidence = {
            "schema_version": EVIDENCE_SCHEMA,
            "candidate": {
                "kind": "canonical-reference-candidate",
                "path": candidate_path.name,
                "sha256": sha256_file(candidate_path),
                "width": candidate.width,
                "height": candidate.height,
                "mode": candidate.mode,
            },
            "source": {"path": source_relative.as_posix(), "sha256": source_digest},
            "target": {"frame_width": frame_width, "frame_height": frame_height},
            "derivation": {
                "normalization": NORMALIZATION_ALGORITHM,
                "outline": OUTLINE_ALGORITHM if enabled else IDENTITY_ALGORITHM,
            },
            "outline": outline_evidence,
            "metrics": {
                "width": candidate.width,
                "height": candidate.height,
                "short_side": min(candidate.size),
                "visible_bbox": bbox,
            },
        }
        evidence_path = destination / "canonical-reference-evidence.json"
        evidence_path.write_text(
            json.dumps(evidence, indent=2) + "\n",
            encoding="utf-8",
        )
        proof = canonical_admission_proof(
            canonical_id,
            candidate_path,
            evidence_path,
            destination,
            outline,
            frame_width,
            frame_height,
            budget=budget,
        )
        proof_payload = {key: value for key, value in proof.items() if not key.startswith("_")}
        (destination / "canonical-admission-proof.json").write_text(
            json.dumps(proof_payload, indent=2) + "\n",
            encoding="utf-8",
        )

    atomic_directory(output_dir, build)
