"""Build and verify deterministic spritesheet evidence packages."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from image_utils import (
    MAX_HIGH_RESOLUTION_SIDE,
    MAX_TARGET_SIDE,
    clear_transparent_rgb,
    resize_premultiplied,
    resolve_high_resolution_dimensions,
)
from PIL import Image, ImageChops, ImageFilter

CANONICAL_REQUEST_SCHEMA = "canonical-authoring-request/v3"
PRODUCTION_REQUEST_SCHEMA = "spritesheet-production-request/v3"
PACKAGE_SCHEMA = "spritesheet-package/v3"
EVIDENCE_SCHEMA = "canonical-reference-evidence/v3"
ADMISSION_PROOF_SCHEMA = "canonical-admission-proof/v1"
NORMALIZATION_ALGORITHM = "normalize-to-canvas/lanczos-premultiplied-v1"
OUTLINE_ALGORITHM = "outward-silhouette-maxfilter/v1"
IDENTITY_ALGORITHM = "identity/v1"
SAMPLER = "lanczos-premultiplied-v1"
SAMPLER_PROOF = (
    "Each cell must exactly equal the recorded algorithm applied directly to its unique high-resolution source."
)
HIGH_RESOLUTION_SHORT_SIDE = 512
FORBIDDEN_TERMS = ("pre-master", "canonical-master", "target-frame", "canonical-lock")
OUTLINE_KEYS = {"enabled", "target_width", "color"}
CONTRACT_KEYS = {
    "frame_width",
    "frame_height",
    "frame_count",
    "high_resolution_short_side",
    "sampler",
    "outline",
    "animation_origin",
    "anchor",
    "safe_bounds",
}
CLIP_KEYS = {
    "id",
    "canonical_reference",
    "direction",
    "camera",
    "loop",
    "repeat_opening_cell",
    "root_motion",
    "transition",
    "terminal_hold",
    "durations_ms",
    "events",
    "frames",
}


class ContractError(ValueError):
    """Raised when a request or package violates the public contract."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{location} must be an object")
    return value


def require_positive_int(value: Any, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ContractError(f"{location} must be a positive integer")
    return value


def read_request(path: Path, schema: str) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read request: {error}") from error
    request = require_object(data, "request")
    if request.get("schema_version") != schema:
        raise ContractError(f"schema_version must be {schema!r}")
    lowered = raw_text.lower()
    forbidden = [term for term in FORBIDDEN_TERMS if term in lowered]
    if forbidden:
        raise ContractError(f"forbidden vocabulary in request: {', '.join(forbidden)}")
    return request


def decode_rgba(data: bytes, location: str) -> Image.Image:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            if opened.format != "PNG":
                raise ContractError(f"{location} must use the PNG container")
            if opened.mode != "RGBA":
                raise ContractError(f"{location} must be RGBA")
            return opened.copy()
    except OSError as error:
        raise ContractError(f"cannot decode {location}: {error}") from error


def open_rgba(path: Path, location: str) -> Image.Image:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"{location} must be a regular non-symlink file: {path}")
    try:
        return decode_rgba(path.read_bytes(), location)
    except OSError as error:
        raise ContractError(f"cannot read {location}: {error}") from error


def normalize_to_canvas(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    ratio = min(size[0] / source.width, size[1] / source.height)
    fitted_size = (max(1, round(source.width * ratio)), max(1, round(source.height * ratio)))
    fitted = resize_premultiplied(source, fitted_size)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return clear_transparent_rgb(canvas)


def apply_outline(
    image: Image.Image,
    target_width: int,
    target_short_side: int,
    color: list[Any],
) -> tuple[Image.Image, int]:
    if (
        len(color) != 4
        or any(
            not isinstance(channel, int)
            or isinstance(channel, bool)
            or not 0 <= channel <= 255
            for channel in color
        )
    ):
        raise ContractError("outline.color must contain four integers between 0 and 255")
    resolved_width = max(
        1,
        round(target_width * HIGH_RESOLUTION_SHORT_SIDE / target_short_side),
    )
    alpha = image.getchannel("A")
    silhouette = alpha.point(lambda value: 255 if value > 0 else 0)
    expanded = silhouette.filter(ImageFilter.MaxFilter(resolved_width * 2 + 1))
    ring = ImageChops.subtract(expanded, silhouette)
    if color[3] != 255:
        ring = ring.point(lambda value: round(value * color[3] / 255))
    outlined = Image.new("RGBA", image.size, tuple(color))
    outlined.putalpha(ring)
    outlined.alpha_composite(image)
    return clear_transparent_rgb(outlined), resolved_width


def atomic_directory(output_dir: Path, build: Callable[[Path], None]) -> None:
    if output_dir.exists():
        raise ContractError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))
    try:
        build(temporary)
        os.replace(temporary, output_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def prepare_canonical(request_path: Path, output_dir: Path) -> None:
    request = read_request(request_path, CANONICAL_REQUEST_SCHEMA)
    require_exact_keys(request, {"schema_version", "canonical_id", "source", "target", "outline"}, "request")
    canonical_id = require_string(request.get("canonical_id"), "canonical_id")
    source_value = request.get("source")
    if not isinstance(source_value, str) or not source_value:
        raise ContractError("source must be a non-empty path string")
    source_path = Path(source_value)
    if not source_path.is_absolute():
        raise ContractError("source must be an absolute path")
    if source_path.is_symlink():
        raise ContractError("source must be a regular non-symlink file")
    try:
        source_bytes = source_path.read_bytes()
    except OSError as error:
        raise ContractError(f"cannot read source: {error}") from error
    source = decode_rgba(source_bytes, "source")
    source_digest = hashlib.sha256(source_bytes).hexdigest()
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
        )
        proof_payload = {key: value for key, value in proof.items() if not key.startswith("_")}
        (destination / "canonical-admission-proof.json").write_text(
            json.dumps(proof_payload, indent=2) + "\n",
            encoding="utf-8",
        )

    atomic_directory(output_dir, build)


def require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{location} must be a non-empty string")
    return value


def require_absolute_path(value: Any, location: str) -> Path:
    path = Path(require_string(value, location))
    if not path.is_absolute():
        raise ContractError(f"{location} must be an absolute path")
    return path


def require_exact_keys(value: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{location} contains unsupported fields: {', '.join(unknown)}")


def validate_outline_contract(value: Any, location: str) -> dict[str, Any]:
    outline = require_object(value, location)
    unknown = sorted(set(outline) - OUTLINE_KEYS)
    if unknown:
        raise ContractError(f"{location} contains unsupported fields: {', '.join(unknown)}")
    enabled = outline.get("enabled")
    if not isinstance(enabled, bool):
        raise ContractError(f"{location}.enabled must be boolean")
    if enabled:
        require_exact_keys(outline, OUTLINE_KEYS, location)
        require_positive_int(outline.get("target_width"), f"{location}.target_width")
        color = outline.get("color")
        if (
            not isinstance(color, list)
            or len(color) != 4
            or any(
                not isinstance(channel, int)
                or isinstance(channel, bool)
                or not 0 <= channel <= 255
                for channel in color
            )
        ):
            raise ContractError(f"{location}.color must contain four integers between 0 and 255")
        if color[3] == 0:
            raise ContractError(f"{location}.color alpha must be greater than zero")
    else:
        require_exact_keys(outline, {"enabled", "target_width"}, location)
        if outline.get("target_width") != "none":
            raise ContractError(f"disabled {location}.target_width must be 'none'")
    return dict(outline)


def validate_point(value: Any, location: str) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise ContractError(f"{location} must contain two integers")
    return list(value)


def validate_bounds(value: Any, location: str, width: int, height: int) -> list[int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
    ):
        raise ContractError(f"{location} must contain four integers")
    left, top, right, bottom = value
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ContractError(f"{location} must fit inside the target cell")
    return list(value)


def normalize_clip_metadata(
    clip: dict[str, Any],
    clip_id: str,
    position_count: int,
    frame_width: int,
    frame_height: int,
) -> dict[str, Any]:
    require_exact_keys(clip, CLIP_KEYS, f"clip {clip_id!r}")
    direction = require_string(clip.get("direction"), f"clip {clip_id!r}.direction")
    camera = require_string(clip.get("camera"), f"clip {clip_id!r}.camera")
    root_motion = require_string(clip.get("root_motion"), f"clip {clip_id!r}.root_motion")
    transition = require_string(clip.get("transition"), f"clip {clip_id!r}.transition")
    terminal_hold = clip.get("terminal_hold")
    if not isinstance(terminal_hold, bool):
        raise ContractError(f"clip {clip_id!r}.terminal_hold must be boolean")
    durations = clip.get("durations_ms")
    if (
        not isinstance(durations, list)
        or len(durations) != position_count
        or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in durations)
    ):
        raise ContractError(
            f"clip {clip_id!r}.durations_ms must contain one positive integer per logical position",
        )
    events = clip.get("events")
    if not isinstance(events, list):
        raise ContractError(f"clip {clip_id!r}.events must be an array")
    normalized_events: list[dict[str, Any]] = []
    for event_index, raw_event in enumerate(events):
        event = require_object(raw_event, f"clip {clip_id!r}.events[{event_index}]")
        require_exact_keys(event, {"name", "position"}, f"clip {clip_id!r}.events[{event_index}]")
        name = require_string(event.get("name"), f"clip {clip_id!r}.events[{event_index}].name")
        position = event.get("position")
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or not 0 <= position < position_count
        ):
            raise ContractError(f"clip {clip_id!r}.events[{event_index}].position is out of range")
        normalized_events.append({"name": name, "position": position})
    return {
        "direction": direction,
        "camera": camera,
        "root_motion": root_motion,
        "transition": transition,
        "terminal_hold": terminal_hold,
        "durations_ms": list(durations),
        "events": normalized_events,
    }


def image_record(
    artifact_id: str,
    artifact_type: str,
    path: str,
    image: Image.Image,
    digest: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "type": artifact_type,
        "path": path,
        "sha256": digest,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        **extra,
    }


def cell_position(index: int, columns: int, rows: int, order: str) -> tuple[int, int]:
    if order == "row-major":
        return index % columns, index // columns
    return index // rows, index % rows


def validate_review_requests(
    reviews_value: Any,
    expected: list[tuple[str, list[str]]],
    source_hashes: dict[str, str],
    admission_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    if not isinstance(reviews_value, list):
        raise ContractError("reviews must be an array")
    if len(reviews_value) != len(expected):
        raise ContractError("reviews must contain one scoped approval for every canonical and clip gate")
    reviews: list[dict[str, Any]] = []
    review_ids: set[str] = set()
    expected_signatures = {(gate, tuple(subject_ids)) for gate, subject_ids in expected}
    actual_signatures: set[tuple[str, tuple[Any, ...]]] = set()
    declared_orders: set[int] = set()
    for index, raw in enumerate(reviews_value):
        review = require_object(raw, f"reviews[{index}]")
        require_exact_keys(
            review,
            {
                "id",
                "gate",
                "subject_ids",
                "subject_sha256",
                "reviewer",
                "evidence",
                "declared_order",
                "admission_sha256",
            },
            f"reviews[{index}]",
        )
        gate = review.get("gate")
        subject_ids = review.get("subject_ids")
        if (
            not isinstance(gate, str)
            or not isinstance(subject_ids, list)
            or any(not isinstance(subject_id, str) for subject_id in subject_ids)
        ):
            raise ContractError(f"reviews[{index}] gate and subject_ids are invalid")
        signature = (gate, tuple(subject_ids))
        if signature not in expected_signatures or signature in actual_signatures:
            raise ContractError(f"reviews[{index}] does not match one required scoped gate")
        actual_signatures.add(signature)
        declared_order = review.get("declared_order")
        if (
            not isinstance(declared_order, int)
            or isinstance(declared_order, bool)
            or not 1 <= declared_order <= len(expected)
            or declared_order in declared_orders
        ):
            raise ContractError("review declared_order must be unique and contiguous")
        declared_orders.add(declared_order)
        expected_hashes = {subject_id: source_hashes[subject_id] for subject_id in subject_ids}
        if review.get("subject_sha256") != expected_hashes:
            raise ContractError(f"{gate} subject_sha256 must bind every subject to current file content")
        canonical_ids = [subject_id for subject_id in subject_ids if subject_id in admission_hashes]
        expected_admissions = {
            canonical_id: admission_hashes[canonical_id]
            for canonical_id in canonical_ids
        }
        if review.get("admission_sha256") != expected_admissions:
            raise ContractError(f"{gate} admission_sha256 must bind the current canonical admission proof")
        review_id = require_string(review.get("id"), f"reviews[{index}].id")
        if review_id in review_ids:
            raise ContractError(f"duplicate review id: {review_id}")
        review_ids.add(review_id)
        require_string(review.get("reviewer"), f"reviews[{index}].reviewer")
        require_string(review.get("evidence"), f"reviews[{index}].evidence")
        reviews.append(dict(review))
    if actual_signatures != expected_signatures or declared_orders != set(range(1, len(expected) + 1)):
        raise ContractError("reviews must cover each required gate exactly once")
    ordered = sorted(reviews, key=lambda review: review["declared_order"])
    gate_rank = {
        "canonical-approval": 0,
        "keyframe-set-approval": 1,
        "sequence-approval": 2,
    }
    ranks = [gate_rank[review["gate"]] for review in ordered]
    if ranks != sorted(ranks):
        raise ContractError(
            "review order must complete every canonical gate before keyframe-set gates and every keyframe-set gate before sequence gates",
        )
    canonical_orders = {
        review["subject_ids"][0]: review["declared_order"]
        for review in ordered
        if review["gate"] == "canonical-approval"
    }
    keyframe_reviews = [review for review in ordered if review["gate"] == "keyframe-set-approval"]
    for review in ordered:
        if review["gate"] not in ("keyframe-set-approval", "sequence-approval"):
            continue
        canonical_id = review["subject_ids"][0]
        if canonical_orders.get(canonical_id, len(expected) + 1) >= review["declared_order"]:
            raise ContractError("canonical approval must precede every dependent clip gate")
        if review["gate"] == "sequence-approval":
            matching_keyframes = [
                keyframe
                for keyframe in keyframe_reviews
                if keyframe["subject_ids"][0] == canonical_id
                and set(keyframe["subject_ids"][1:]).issubset(set(review["subject_ids"][1:]))
            ]
            if (
                len(matching_keyframes) != 1
                or matching_keyframes[0]["declared_order"] >= review["declared_order"]
            ):
                raise ContractError("keyframe-set approval must precede its sequence approval")
    return ordered


def canonical_admission_proof(
    canonical_id: str,
    canonical_path: Path,
    evidence_path: Path,
    evidence_root: Path,
    contract_outline: dict[str, Any],
    frame_width: int,
    frame_height: int,
) -> dict[str, Any]:
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise ContractError(f"canonical reference {canonical_id!r} evidence_path must be a regular file")
    try:
        evidence = require_object(json.loads(evidence_path.read_text(encoding="utf-8")), "canonical evidence")
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read canonical evidence: {error}") from error
    require_exact_keys(
        evidence,
        {"schema_version", "candidate", "source", "target", "derivation", "outline", "metrics"},
        "canonical evidence",
    )
    if evidence.get("schema_version") != EVIDENCE_SCHEMA:
        raise ContractError(f"canonical evidence schema_version must be {EVIDENCE_SCHEMA!r}")
    candidate = require_object(evidence.get("candidate"), "canonical evidence.candidate")
    require_exact_keys(candidate, {"kind", "path", "sha256", "width", "height", "mode"}, "canonical evidence.candidate")
    canonical = open_rgba(canonical_path, f"canonical reference {canonical_id!r}")
    canonical_hash = sha256_file(canonical_path)
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
    source_path = (evidence_root / source_relative).resolve()
    if (
        source_relative.is_absolute()
        or ".." in source_relative.parts
        or source_value != source_relative.as_posix()
        or source_value != f"evidence/{source_record.get('sha256')}.png"
        or not source_path.is_relative_to(evidence_root.resolve())
        or source_path.is_symlink()
        or not source_path.is_file()
        or sha256_file(source_path) != source_record.get("sha256")
    ):
        raise ContractError(f"canonical reference {canonical_id!r} source hash does not match evidence")
    source = open_rgba(source_path, "canonical evidence source")
    expected_size, _ = resolve_high_resolution_dimensions(frame_width, frame_height)
    normalized = normalize_to_canvas(source, expected_size)
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
    return {
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
        "authoring_evidence_sha256": sha256_file(evidence_path),
        "_source_path": source_path,
        "_evidence_path": evidence_path,
    }


def parse_production_request(request_path: Path) -> dict[str, Any]:
    request = read_request(request_path, PRODUCTION_REQUEST_SCHEMA)
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
    canonical: dict[str, dict[str, Any]] = {}
    admissions: dict[str, dict[str, Any]] = {}
    images: dict[str, Image.Image] = {}
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
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
        image = open_rgba(path, f"canonical_references[{index}].path")
        if image.size != expected_high_resolution_size:
            raise ContractError("canonical reference has wrong high-resolution canvas")
        canonical[artifact_id] = dict(entry)
        images[artifact_id] = image
        paths[artifact_id] = path
        hashes[artifact_id] = sha256_file(path)
        proof = canonical_admission_proof(
            artifact_id,
            path,
            evidence_path,
            evidence_path.parent,
            normalized_outline,
            frame_width,
            frame_height,
        )
        proof_payload = {key: value for key, value in proof.items() if not key.startswith("_")}
        expected_proof_bytes = (json.dumps(proof_payload, indent=2) + "\n").encode("utf-8")
        try:
            proof_bytes = proof_path.read_bytes()
            supplied_proof = require_object(json.loads(proof_bytes), "canonical admission proof")
        except (OSError, json.JSONDecodeError) as error:
            raise ContractError(f"cannot read canonical admission proof: {error}") from error
        if supplied_proof != proof_payload or proof_bytes != expected_proof_bytes:
            raise ContractError("canonical admission proof must exactly match prepare-canonical replay output")
        admissions[artifact_id] = {
            "proof": proof_payload,
            "proof_bytes": proof_bytes,
            "proof_sha256": hashlib.sha256(proof_bytes).hexdigest(),
            "source_path": proof["_source_path"],
            "evidence_path": proof["_evidence_path"],
            "evidence_sha256": proof_payload["authoring_evidence_sha256"],
        }

    clips_value = request.get("clips")
    if not isinstance(clips_value, list) or not clips_value:
        raise ContractError("clips must be a non-empty array")
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
        raw_frames = clip.get("frames")
        if not isinstance(raw_frames, list) or not raw_frames:
            raise ContractError(f"clip {clip_id!r} frames must be a non-empty array")
        clip_metadata = normalize_clip_metadata(
            clip,
            clip_id,
            len(raw_frames) + int(repeat),
            frame_width,
            frame_height,
        )
        normalized_frames: list[dict[str, Any]] = []
        local_keyframe_indices: list[int] = []
        for frame_index, raw_frame in enumerate(raw_frames):
            frame = require_object(raw_frame, f"clips[{clip_index}].frames[{frame_index}]")
            frame_id = require_string(frame.get("id"), f"clips[{clip_index}].frames[{frame_index}].id")
            if frame_id == "spritesheet":
                raise ContractError("'spritesheet' is a reserved artifact id")
            if frame_id in images:
                raise ContractError(f"duplicate artifact id: {frame_id}")
            role = frame.get("role")
            if role not in ("keyframe", "in-between"):
                raise ContractError(f"frame {frame_id!r} role must be keyframe or in-between")
            expected_frame_keys = {"id", "role", "path"}
            if role == "in-between":
                expected_frame_keys |= {"previous_keyframe", "next_keyframe"}
            require_exact_keys(frame, expected_frame_keys, f"frame {frame_id!r}")
            path = require_absolute_path(frame.get("path"), f"frame {frame_id!r}.path")
            image = open_rgba(path, f"frame {frame_id!r}.path")
            if image.size != expected_high_resolution_size:
                raise ContractError(f"frame {frame_id!r} has wrong high-resolution canvas")
            images[frame_id] = image
            paths[frame_id] = path
            hashes[frame_id] = sha256_file(path)
            frame_ids.append(frame_id)
            if role == "keyframe":
                local_keyframe_indices.append(frame_index)
                if "previous_keyframe" in frame or "next_keyframe" in frame:
                    raise ContractError(f"keyframe {frame_id!r} cannot declare brackets")
            normalized_frames.append(dict(frame))
        if len(local_keyframe_indices) < 2:
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
        if sum(frame["role"] == "in-between" for frame in normalized_frames) < 2:
            raise ContractError(f"clip {clip_id!r} requires at least two distinct in-betweens")
        total_cells += len(normalized_frames) + int(repeat)
        clip_review_scopes.extend(
            (
                (
                    "keyframe-set-approval",
                    [canonical_id, *[frame["id"] for frame in normalized_frames if frame["role"] == "keyframe"]],
                ),
                ("sequence-approval", [canonical_id, *[frame["id"] for frame in normalized_frames]]),
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
    if len(set(high_resolution_pixel_hashes)) != len(high_resolution_pixel_hashes):
        raise ContractError("all high-resolution frame images must have distinct pixels")
    canonical_pixel_hashes = [pixel_hashes[canonical_id] for canonical_id in canonical]
    if len(set(canonical_pixel_hashes)) != len(canonical_pixel_hashes):
        raise ContractError("canonical references must have distinct pixels; share one ID when content is shared")
    if set(canonical_pixel_hashes) & set(high_resolution_pixel_hashes):
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
    return {
        "contract": dict(contract),
        "frame_width": frame_width,
        "frame_height": frame_height,
        "frame_count": frame_count,
        "high_resolution_size": expected_high_resolution_size,
        "animation_origin": animation_origin,
        "anchor": anchor,
        "safe_bounds": safe_bounds,
        "canonical_ids": list(canonical),
        "images": images,
        "paths": paths,
        "hashes": hashes,
        "admissions": admissions,
        "clips": clips,
        "frame_ids": frame_ids,
        "reviews": reviews,
        "columns": columns,
        "order": order,
    }


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
                shutil.copyfile(admission["source_path"], source_destination)
            evidence_hash = admission["evidence_sha256"]
            evidence_relative = f"evidence/{evidence_hash}.json"
            shutil.copyfile(admission["evidence_path"], destination / evidence_relative)
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
            source_path = parsed["paths"][artifact_id]
            digest = parsed["hashes"][artifact_id]
            relative = f"artifacts/{digest}.png"
            destination_path = destination / relative
            if not destination_path.exists():
                shutil.copyfile(source_path, destination_path)
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
                        "high-resolution-frame",
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

        sampled = {
            frame_id: resize_premultiplied(
                parsed["images"][frame_id],
                (parsed["frame_width"], parsed["frame_height"]),
            )
            for frame_id in parsed["frame_ids"]
        }
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
        sheet = Image.new(
            "RGBA",
            (columns * parsed["frame_width"], rows * parsed["frame_height"]),
            (0, 0, 0, 0),
        )
        for index, cell in enumerate(cells):
            column, row = cell_position(index, columns, rows, parsed["order"])
            x = column * parsed["frame_width"]
            y = row * parsed["frame_height"]
            sheet.alpha_composite(sampled[cell["source"]], (x, y))
            cell.update({"index": index, "column": column, "row": row})
        sheet_path = destination / "spritesheet.png"
        clear_transparent_rgb(sheet).save(sheet_path)
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
            "sampling": {
                "algorithm": SAMPLER,
                "proof": SAMPLER_PROOF,
            },
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
        if not verify_package(manifest_path, emit=False):
            raise ContractError("generated package did not pass verification")

    atomic_directory(output_dir, build)


def verify_package(manifest_path: Path, *, emit: bool = True) -> bool:
    failures: list[str] = []
    declarations: list[str] = []
    reviewed: list[str] = []

    def check(condition: bool, location: str, detail: str) -> None:
        if not condition:
            failures.append(f"FAIL MACHINE-VERIFIED {location}: {detail}")

    check(manifest_path.name == "manifest.json", "manifest.path", "authoritative manifest must be named manifest.json")

    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"FAIL MACHINE-VERIFIED manifest: cannot read JSON: {error}")
        data = {}
        raw_text = ""
    check(isinstance(data, dict), "$", "manifest must be an object")
    if not isinstance(data, dict):
        data = {}
    check(data.get("schema_version") == PACKAGE_SCHEMA, "schema_version", f"required={PACKAGE_SCHEMA!r}")
    check(
        set(data) == {"schema_version", "contract", "artifacts", "canonical_admissions", "clips", "reviews", "sampling", "assembly"},
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
    )
    check(dimensions_valid, "contract.dimensions", "positive target dimensions must have shortest side below 512")
    check(contract.get("high_resolution_short_side") == 512, "contract.high_resolution_short_side", "required=512")
    check(contract.get("sampler") == SAMPLER, "contract.sampler", f"required={SAMPLER}")
    check(set(contract) == CONTRACT_KEYS, "contract.fields", f"required={sorted(CONTRACT_KEYS)}")
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
    declarations.append(
        "INFO DECLARED sampler: the manifest declares the sampler; verification recomputes current cell pixels and does not prove historical resize count",
    )
    artifacts_value = data.get("artifacts")
    check(isinstance(artifacts_value, list), "artifacts", "must be an array")
    artifacts: dict[str, dict[str, Any]] = {}
    images: dict[str, Image.Image] = {}
    artifact_relative_paths: set[str] = set()
    package_root = base_dir.resolve()
    allowed_types = {"canonical-reference", "high-resolution-frame", "spritesheet"}
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
            path = (base_dir / raw_path).resolve()
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
            actual_hash = sha256_file(path)
            check(actual_hash == raw.get("sha256"), f"{location}.sha256", "file content must match manifest")
            try:
                image = open_rgba(path, f"{location}.path")
            except ContractError as error:
                check(False, f"{location}.image", str(error))
                continue
            images[artifact_id] = image
            base_artifact_keys = {"id", "type", "path", "sha256", "width", "height", "mode"}
            expected_artifact_keys = base_artifact_keys
            if artifact_type == "high-resolution-frame":
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
            if dimensions_valid and artifact_type in ("canonical-reference", "high-resolution-frame"):
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
            proof_path = (base_dir / proof_value).resolve() if isinstance(proof_value, str) else base_dir
            source_path = (base_dir / source_value).resolve() if isinstance(source_value, str) else base_dir
            evidence_path = (base_dir / evidence_value).resolve() if isinstance(evidence_value, str) else base_dir
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
            actual_proof_hash = sha256_file(proof_path)
            actual_source_hash = sha256_file(source_path)
            actual_evidence_hash = sha256_file(evidence_path)
            check(actual_proof_hash == proof_hash, f"{location}.proof_sha256", "proof bytes must match")
            check(actual_source_hash == source_hash, f"{location}.source_sha256", "source bytes must match")
            check(actual_evidence_hash == evidence_hash, f"{location}.evidence_sha256", "evidence bytes must match")
            try:
                proof = require_object(json.loads(proof_path.read_text(encoding="utf-8")), "admission proof")
                require_exact_keys(
                    proof,
                    {
                        "schema_version", "canonical_reference", "target", "source", "outline",
                        "derivation", "authoring_evidence_sha256",
                    },
                    "admission proof",
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
                source = open_rgba(source_path, "admission source")
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
                normalized = normalize_to_canvas(source, expected_size)
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
                    evidence_path,
                    base_dir,
                    proof_outline,
                    width,
                    height,
                )
                replayed_payload = {
                    key: value for key, value in replayed_proof.items() if not key.startswith("_")
                }
                if proof != replayed_payload:
                    raise ContractError("admission proof must exactly match independent evidence replay")
            except (ContractError, OSError, json.JSONDecodeError, TypeError) as error:
                check(False, location, str(error))
            else:
                if canonical_id in admission_hashes:
                    check(False, f"{location}.canonical_reference", "must be unique")
                admission_hashes[canonical_id] = actual_proof_hash
    clips_value = data.get("clips")
    check(isinstance(clips_value, list) and bool(clips_value), "clips", "must be a non-empty array")
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
                    and artifacts[frame_id].get("type") == "high-resolution-frame"
                    and artifacts[frame_id].get("role") == role,
                    f"frame[{frame_id}].artifact",
                    "must reference a matching high-resolution-frame artifact",
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
        "high-resolution-frame.pixels",
        "all high-resolution frames must have distinct pixels",
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
    if replay_safe and sheet is not None:
        check(sheet.size == (columns * width, rows * height), "assembly.sheet.dimensions", "must match the fixed grid")
        pixel_match = True
        used: set[tuple[int, int]] = set()
        if isinstance(cells, list):
            for index, (source, _) in enumerate(expected_sources):
                column, row = cell_position(index, columns, rows, order)
                used.add((column, row))
                if source not in images:
                    pixel_match = False
                    continue
                expected = resize_premultiplied(images[source], (width, height)).tobytes()
                actual = sheet.crop(
                    (column * width, row * height, (column + 1) * width, (row + 1) * height),
                ).tobytes()
                pixel_match = pixel_match and actual == expected
        check(
            pixel_match,
            "cells",
            "each cell must exactly equal the recorded algorithm applied directly to its unique high-resolution source",
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
    sampling = data.get("sampling") if isinstance(data.get("sampling"), dict) else {}
    check(sampling.get("algorithm") == SAMPLER, "sampling.algorithm", f"required={SAMPLER}")
    check(sampling.get("proof") == SAMPLER_PROOF, "sampling.proof", "must state the exact replay obligation")
    check(
        set(sampling) == {"algorithm", "proof"},
        "sampling.fields",
        "sampling records only the replayable algorithm and proof obligation",
    )
    declarations.append(
        "INFO DECLARED generation: canonical references are declared visual references and in-between brackets are declared creative relationships",
    )
    if emit:
        for failure in failures:
            print(failure)
        if not failures:
            print(
                "PASS MACHINE-VERIFIED cells: each cell exactly equals the recorded algorithm applied directly to its unique high-resolution source",
            )
        for declaration in declarations:
            print(declaration)
        for review in reviewed:
            print(review)
        print(f"machine_failures={len(failures)}")
    return not failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Public schemas:\n"
            "  canonical-authoring-request/v3 -> canonical review candidate + replay evidence\n"
            "  spritesheet-production-request/v3 -> admission-bound immutable spritesheet package\n"
            "  spritesheet-package/v3 -> independently replayed authoritative manifest"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser(
        "prepare-canonical",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Consume canonical-authoring-request/v3. Required fields:\n"
            "  canonical_id: production canonical-reference artifact ID\n"
            "  source: absolute path to a regular non-symlink RGBA PNG\n"
            "  target: frame_width, frame_height\n"
            "  outline: enabled, target_width, and color (RGBA array) only when enabled\n"
            "The command atomically emits a candidate, source evidence, authoring evidence, and admission proof."
        ),
    )
    prepare.add_argument("--request", required=True, type=Path, help="canonical-authoring-request/v3 JSON")
    prepare.add_argument("--output-dir", required=True, type=Path, help="new atomic candidate directory")
    build = subparsers.add_parser(
        "build-package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Consume spritesheet-production-request/v3. Required sections:\n"
            "  contract: dimensions, 512 high-resolution side, sampler, conditional outline, origin, anchor, safe bounds\n"
            "  canonical_references: id + absolute regular candidate, evidence_path, and proof_path\n"
            "  clips: runtime metadata + ordered keyframe/in-between records with absolute RGBA PNG paths\n"
            "  reviews: hash-bound canonical, keyframe-set, and sequence approvals\n"
            "  grid: columns + row-major or column-major order"
        ),
    )
    build.add_argument("--request", required=True, type=Path, help="spritesheet-production-request/v3 JSON")
    build.add_argument("--output-dir", required=True, type=Path, help="new atomic package directory")
    verify = subparsers.add_parser(
        "verify-package",
        description="Verify a spritesheet-package/v3 manifest, replay canonical admission and every cell, and emit MACHINE-VERIFIED, DECLARED, and REVIEWED results.",
    )
    verify.add_argument("--manifest", required=True, type=Path, help="package-relative authoritative manifest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "prepare-canonical":
            prepare_canonical(args.request, args.output_dir)
        elif args.command == "build-package":
            build_package(args.request, args.output_dir)
        elif args.command == "verify-package":
            if not verify_package(args.manifest):
                return 1
        else:
            raise ContractError(f"{args.command} is not implemented")
    except (ContractError, OSError, ValueError, TypeError, KeyError, IndexError) as error:
        print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
