"""Closed-field codecs and protocol constants for spritesheet contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ContractError
from .package_io import ResourceBudget, read_regular_file_snapshot

CANONICAL_REQUEST_SCHEMA = "canonical-authoring-request/v3"
PRODUCTION_REQUEST_SCHEMA = "spritesheet-production-request/v4"
PACKAGE_SCHEMA = "spritesheet-package/v4"
EVIDENCE_SCHEMA = "canonical-reference-evidence/v3"
ADMISSION_PROOF_SCHEMA = "canonical-admission-proof/v1"
NORMALIZATION_ALGORITHM = "normalize-to-canvas/lanczos-premultiplied-v1"
OUTLINE_ALGORITHM = "outward-silhouette-maxfilter/v1"
IDENTITY_ALGORITHM = "identity/v1"
SAMPLER = "lanczos-premultiplied-v1"
RENDERING_RECEIPT_SCHEMA = "spritesheet-rendering-receipt/v1"
RENDERING_PIPELINE = "high-resolution-outline-then-target-resize/v1"
MASK_POLICY = "nonzero-alpha/v1"
HIGH_RESOLUTION_SHORT_SIDE = 512
MAX_JSON_FILE_BYTES = 8 * 1024 * 1024
MAX_FRAME_COUNT = 4096
MAX_CANONICAL_REFERENCES = 256
MAX_CLIPS = 256
MAX_REVIEWS = 768
FORBIDDEN_TERMS = ("pre-master", "canonical-master", "target-frame", "canonical-lock")
OUTLINE_KEYS = {"enabled", "target_width", "color"}
CONTRACT_KEYS = {
    "frame_width", "frame_height", "frame_count", "high_resolution_short_side",
    "sampler", "outline", "animation_origin", "anchor", "safe_bounds",
}
CLIP_KEYS = {
    "id", "canonical_reference", "direction", "camera", "loop",
    "repeat_opening_cell", "root_motion", "transition", "terminal_hold",
    "durations_ms", "events", "frames",
}


def require_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{location} must be an object")
    return value


def require_positive_int(value: Any, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ContractError(f"{location} must be a positive integer")
    return value


def read_request(
    path: Path,
    schema: str,
    *,
    budget: ResourceBudget | None = None,
) -> dict[str, Any]:
    try:
        snapshot = read_regular_file_snapshot(
            path,
            "request",
            MAX_JSON_FILE_BYTES,
            budget=budget,
        )
        raw_text = snapshot.data.decode("utf-8")
        data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read request: {error}") from error
    request = require_object(data, "request")
    if request.get("schema_version") != schema:
        raise ContractError(f"schema_version must be {schema!r}")
    lowered = raw_text.lower()
    forbidden = [term for term in FORBIDDEN_TERMS if term in lowered]
    if forbidden:
        raise ContractError(f"forbidden vocabulary in request: {', '.join(forbidden)}")
    return request


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


def validate_review_requests(
    reviews_value: Any,
    expected: list[tuple[str, list[str]]],
    source_hashes: dict[str, str],
    admission_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    if not isinstance(reviews_value, list):
        raise ContractError("reviews must be an array")
    if len(reviews_value) > MAX_REVIEWS:
        raise ContractError(f"reviews must not exceed {MAX_REVIEWS} entries")
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
