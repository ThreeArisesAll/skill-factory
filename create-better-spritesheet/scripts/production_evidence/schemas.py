"""Closed validators for spritesheet production evidence schemas."""

from __future__ import annotations

import math
from typing import Any

from .errors import EvidenceError
from .io import canonical_sha256, validate_sha256

IDENTITY_SCHEMA = "identity-bible/v1"
BLUEPRINT_SCHEMA = "motion-blueprint/v1"
SPACING_SCHEMA = "spacing-plan/v1"
DIAGNOSTICS_SCHEMA = "motion-diagnostics/v1"
REVIEW_SCHEMA = "review-packet/v1"
RUNTIME_SCHEMA = "runtime-playback-proof/v1"
RUNTIME_PROJECTION_SCHEMA = "spritesheet-runtime-projection/v1"
DELIVERY_SCHEMA = "spritesheet-production-delivery/v1"
DELIVERY_STATUSES = {"package-ready", "runtime-metadata-complete", "runtime-verified"}
EVIDENCE_KINDS = {
    "canonical-board",
    "contact-sheet",
    "native-size-frame",
    "onion-skin",
    "loop-capture",
    "one-shot-capture",
    "runtime-capture",
}
MAX_ARRAY_ITEMS = 4096


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must be an object")
    return value


def _array(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must be an array")
    if len(value) > MAX_ARRAY_ITEMS:
        raise EvidenceError(
            "RESOURCE_LIMIT", f"{location} exceeds {MAX_ARRAY_ITEMS} items"
        )
    return value


def _keys(value: dict[str, Any], expected: set[str], location: str) -> None:
    if set(value) != expected:
        raise EvidenceError(
            "SCHEMA_INVALID",
            f"{location} fields must be exactly {sorted(expected)}",
        )


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("SCHEMA_INVALID", f"{location} must be a non-empty string")
    return value


def _boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must be boolean")
    return value


def _integer(value: Any, location: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location} must be an integer >= {minimum}"
        )
    return value


def _string_array(value: Any, location: str) -> list[str]:
    items = _array(value, location)
    for index, item in enumerate(items):
        _string(item, f"{location}[{index}]")
    return items


def _ref(value: Any, location: str, *, request: bool = False) -> None:
    item = _object(value, location)
    path_key = "path" if request else "ref"
    _keys(item, {path_key, "sha256"}, location)
    _string(item[path_key], f"{location}.{path_key}")
    validate_sha256(item["sha256"], f"{location}.sha256")


def _approval(value: Any, subject: dict[str, Any], location: str) -> None:
    approval = _object(value, location)
    _keys(approval, {"status", "subject_sha256", "reviewer", "evidence"}, location)
    if approval.get("status") not in {"approved", "rejected"}:
        raise EvidenceError("SCHEMA_INVALID", f"{location}.status is invalid")
    validate_sha256(approval.get("subject_sha256"), f"{location}.subject_sha256")
    if approval["subject_sha256"] != canonical_sha256(subject):
        raise EvidenceError(
            "APPROVAL_HASH_MISMATCH", f"{location} does not bind the canonical content"
        )
    _string(approval.get("reviewer"), f"{location}.reviewer")
    _string(approval.get("evidence"), f"{location}.evidence")


def validate_identity(value: dict[str, Any]) -> None:
    _keys(
        value,
        {"schema_version", "identity_id", "content", "approval"},
        "identity bible",
    )
    _string(value.get("identity_id"), "identity bible.identity_id")
    content = _object(value.get("content"), "identity bible.content")
    _keys(
        content,
        {
            "subject",
            "canonical_bindings",
            "invariants",
            "allowed_variations",
            "forbidden_drifts",
        },
        "identity bible.content",
    )
    _string(content.get("subject"), "identity bible.content.subject")
    for index, raw in enumerate(
        _array(
            content.get("canonical_bindings"),
            "identity bible.content.canonical_bindings",
        )
    ):
        item = _object(raw, f"identity bible.content.canonical_bindings[{index}]")
        _keys(
            item,
            {
                "canonical_id",
                "direction",
                "camera",
                "candidate_sha256",
                "admission_proof_sha256",
            },
            f"identity bible.content.canonical_bindings[{index}]",
        )
        for key in ("canonical_id", "direction", "camera"):
            _string(
                item.get(key),
                f"identity bible.content.canonical_bindings[{index}].{key}",
            )
        validate_sha256(
            item.get("candidate_sha256"),
            f"identity bible.content.canonical_bindings[{index}].candidate_sha256",
        )
        validate_sha256(
            item.get("admission_proof_sha256"),
            f"identity bible.content.canonical_bindings[{index}].admission_proof_sha256",
        )
    for field, expected in (
        ("invariants", {"id", "scope", "statement", "evidence_refs"}),
        ("allowed_variations", {"id", "statement"}),
        ("forbidden_drifts", {"id", "statement"}),
    ):
        for index, raw in enumerate(
            _array(content.get(field), f"identity bible.content.{field}")
        ):
            item = _object(raw, f"identity bible.content.{field}[{index}]")
            _keys(item, expected, f"identity bible.content.{field}[{index}]")
            for key in expected - {"evidence_refs"}:
                _string(item.get(key), f"identity bible.content.{field}[{index}].{key}")
            if "evidence_refs" in expected:
                _string_array(
                    item.get("evidence_refs"),
                    f"identity bible.content.{field}[{index}].evidence_refs",
                )
    _approval(
        value.get("approval"),
        {
            "schema_version": IDENTITY_SCHEMA,
            "identity_id": value["identity_id"],
            "content": content,
        },
        "identity bible.approval",
    )


def validate_blueprint(value: dict[str, Any]) -> None:
    _keys(
        value,
        {"schema_version", "blueprint_id", "content", "approval"},
        "motion blueprint",
    )
    _string(value.get("blueprint_id"), "motion blueprint.blueprint_id")
    content = _object(value.get("content"), "motion blueprint.content")
    _keys(
        content,
        {
            "identity_bible_sha256",
            "clip_id",
            "canonical_id",
            "intent",
            "direction",
            "camera",
            "entry",
            "exit",
            "loop",
            "root_motion",
            "action_evidence",
            "positions",
        },
        "motion blueprint.content",
    )
    validate_sha256(
        content.get("identity_bible_sha256"),
        "motion blueprint.content.identity_bible_sha256",
    )
    for key in (
        "clip_id",
        "canonical_id",
        "intent",
        "direction",
        "camera",
        "entry",
        "exit",
        "root_motion",
    ):
        _string(content.get(key), f"motion blueprint.content.{key}")
    _boolean(content.get("loop"), "motion blueprint.content.loop")
    action_evidence = _array(
        content.get("action_evidence"), "motion blueprint.content.action_evidence"
    )
    if not action_evidence:
        raise EvidenceError(
            "SCHEMA_INVALID",
            "motion blueprint.content.action_evidence must be non-empty",
        )
    for index, raw in enumerate(action_evidence):
        item = _object(raw, f"motion blueprint.content.action_evidence[{index}]")
        _keys(
            item,
            {"evidence_id", "ref", "relationship"},
            f"motion blueprint.content.action_evidence[{index}]",
        )
        _string(
            item.get("evidence_id"),
            f"motion blueprint.content.action_evidence[{index}].evidence_id",
        )
        _string(
            item.get("ref"), f"motion blueprint.content.action_evidence[{index}].ref"
        )
        if item.get("relationship") not in {"supplied-reference", "written-intent"}:
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"motion blueprint.content.action_evidence[{index}].relationship is invalid",
            )
    position_keys = {
        "frame_id",
        "index",
        "role",
        "phase",
        "action_beat",
        "purpose",
        "pose",
        "orientation",
        "projection",
        "depth_and_occlusion",
        "root_and_alpha_centroid_intent",
        "contacts",
        "transition_from_previous",
        "transition_to_next",
        "duration_ms",
        "events",
        "previous_keyframe",
        "next_keyframe",
    }
    for index, raw in enumerate(
        _array(content.get("positions"), "motion blueprint.content.positions")
    ):
        item = _object(raw, f"motion blueprint.content.positions[{index}]")
        _keys(item, position_keys, f"motion blueprint.content.positions[{index}]")
        for key in position_keys - {
            "index",
            "duration_ms",
            "events",
            "contacts",
            "previous_keyframe",
            "next_keyframe",
        }:
            _string(item.get(key), f"motion blueprint.content.positions[{index}].{key}")
        if item.get("role") != "keyframe":
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"motion blueprint.content.positions[{index}].role must be keyframe",
            )
        _integer(
            item.get("index"), f"motion blueprint.content.positions[{index}].index"
        )
        _integer(
            item.get("duration_ms"),
            f"motion blueprint.content.positions[{index}].duration_ms",
            minimum=1,
        )
        _string_array(
            item.get("events"), f"motion blueprint.content.positions[{index}].events"
        )
        _string_array(
            item.get("contacts"),
            f"motion blueprint.content.positions[{index}].contacts",
        )
        for key in ("previous_keyframe", "next_keyframe"):
            if item.get(key) is not None:
                _string(item[key], f"motion blueprint.content.positions[{index}].{key}")
    _approval(
        value.get("approval"),
        {
            "schema_version": BLUEPRINT_SCHEMA,
            "blueprint_id": value["blueprint_id"],
            "content": content,
        },
        "motion blueprint.approval",
    )


def validate_spacing(value: dict[str, Any]) -> None:
    _keys(
        value,
        {"schema_version", "spacing_plan_id", "content", "approval"},
        "spacing plan",
    )
    _string(value.get("spacing_plan_id"), "spacing plan.spacing_plan_id")
    content = _object(value.get("content"), "spacing plan.content")
    _keys(
        content,
        {"motion_blueprint_sha256", "clip_id", "approved_keyframes", "positions"},
        "spacing plan.content",
    )
    validate_sha256(
        content.get("motion_blueprint_sha256"),
        "spacing plan.content.motion_blueprint_sha256",
    )
    _string(content.get("clip_id"), "spacing plan.content.clip_id")
    for index, raw in enumerate(
        _array(
            content.get("approved_keyframes"), "spacing plan.content.approved_keyframes"
        )
    ):
        item = _object(raw, f"spacing plan.content.approved_keyframes[{index}]")
        _keys(
            item,
            {"frame_id", "source_sha256"},
            f"spacing plan.content.approved_keyframes[{index}]",
        )
        _string(
            item.get("frame_id"),
            f"spacing plan.content.approved_keyframes[{index}].frame_id",
        )
        validate_sha256(
            item.get("source_sha256"),
            f"spacing plan.content.approved_keyframes[{index}].source_sha256",
        )
    position_keys = {
        "frame_id",
        "index",
        "role",
        "previous_keyframe",
        "next_keyframe",
        "duration_ms",
        "events",
        "spacing",
        "arc",
        "contacts",
        "transition_from_previous",
        "transition_to_next",
    }
    for index, raw in enumerate(
        _array(content.get("positions"), "spacing plan.content.positions")
    ):
        item = _object(raw, f"spacing plan.content.positions[{index}]")
        _keys(item, position_keys, f"spacing plan.content.positions[{index}]")
        _string(
            item.get("frame_id"), f"spacing plan.content.positions[{index}].frame_id"
        )
        _integer(item.get("index"), f"spacing plan.content.positions[{index}].index")
        if item.get("role") not in {"keyframe", "in-between", "closing-alias"}:
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"spacing plan.content.positions[{index}].role is invalid",
            )
        for key in ("previous_keyframe", "next_keyframe"):
            if item.get(key) is not None:
                _string(item[key], f"spacing plan.content.positions[{index}].{key}")
        _integer(
            item.get("duration_ms"),
            f"spacing plan.content.positions[{index}].duration_ms",
            minimum=1,
        )
        _string_array(
            item.get("events"), f"spacing plan.content.positions[{index}].events"
        )
        _string(item.get("spacing"), f"spacing plan.content.positions[{index}].spacing")
        _string(item.get("arc"), f"spacing plan.content.positions[{index}].arc")
        _string_array(
            item.get("contacts"), f"spacing plan.content.positions[{index}].contacts"
        )
        _string(
            item.get("transition_from_previous"),
            f"spacing plan.content.positions[{index}].transition_from_previous",
        )
        _string(
            item.get("transition_to_next"),
            f"spacing plan.content.positions[{index}].transition_to_next",
        )
    _approval(
        value.get("approval"),
        {
            "schema_version": SPACING_SCHEMA,
            "spacing_plan_id": value["spacing_plan_id"],
            "content": content,
        },
        "spacing plan.approval",
    )


def validate_diagnostics(value: dict[str, Any]) -> None:
    _keys(
        value,
        {
            "schema_version",
            "package_manifest",
            "assets",
            "previews",
            "clips",
            "observations",
        },
        "motion diagnostics",
    )
    _ref(value.get("package_manifest"), "motion diagnostics.package_manifest")
    assets = _object(value.get("assets"), "motion diagnostics.assets")
    _keys(
        assets,
        {"contact_sheet", "native_size_board", "onion_skin"},
        "motion diagnostics.assets",
    )
    for key, ref in assets.items():
        _ref(ref, f"motion diagnostics.assets.{key}")
    preview_clip_ids: set[str] = set()
    for index, preview in enumerate(
        _array(value.get("previews"), "motion diagnostics.previews")
    ):
        item = _object(preview, f"motion diagnostics.previews[{index}]")
        _keys(item, {"clip_id", "asset"}, f"motion diagnostics.previews[{index}]")
        preview_clip_id = _string(
            item.get("clip_id"), f"motion diagnostics.previews[{index}].clip_id"
        )
        if preview_clip_id in preview_clip_ids:
            raise EvidenceError(
                "SCHEMA_INVALID", "motion diagnostics previews must be unique per clip"
            )
        preview_clip_ids.add(preview_clip_id)
        _ref(item.get("asset"), f"motion diagnostics.previews[{index}].asset")
    diagnostic_clip_ids: set[str] = set()
    for clip_index, raw_clip in enumerate(
        _array(value.get("clips"), "motion diagnostics.clips")
    ):
        clip = _object(raw_clip, f"motion diagnostics.clips[{clip_index}]")
        _keys(clip, {"clip_id", "cells"}, f"motion diagnostics.clips[{clip_index}]")
        diagnostic_clip_id = _string(
            clip.get("clip_id"), f"motion diagnostics.clips[{clip_index}].clip_id"
        )
        if diagnostic_clip_id in diagnostic_clip_ids:
            raise EvidenceError(
                "SCHEMA_INVALID", "motion diagnostics clips must be unique"
            )
        diagnostic_clip_ids.add(diagnostic_clip_id)
        for cell_index, raw_cell in enumerate(
            _array(clip.get("cells"), f"motion diagnostics.clips[{clip_index}].cells")
        ):
            cell = _object(
                raw_cell, f"motion diagnostics.clips[{clip_index}].cells[{cell_index}]"
            )
            _keys(
                cell,
                {
                    "index",
                    "source",
                    "alpha_bbox",
                    "alpha_area",
                    "alpha_centroid",
                    "anchor_offset",
                    "safe_bounds_overflow",
                    "clipped_edges",
                    "pixel_diff_from_previous",
                },
                f"motion diagnostics.clips[{clip_index}].cells[{cell_index}]",
            )
            _integer(
                cell.get("index"),
                f"motion diagnostics.clips[{clip_index}].cells[{cell_index}].index",
            )
            _string(
                cell.get("source"),
                f"motion diagnostics.clips[{clip_index}].cells[{cell_index}].source",
            )
            _integer(
                cell.get("alpha_area"),
                f"motion diagnostics.clips[{clip_index}].cells[{cell_index}].alpha_area",
            )
            _string_array(
                cell.get("clipped_edges"),
                f"motion diagnostics.clips[{clip_index}].cells[{cell_index}].clipped_edges",
            )
            if any(
                edge not in {"left", "top", "right", "bottom"}
                for edge in cell["clipped_edges"]
            ):
                raise EvidenceError(
                    "SCHEMA_INVALID",
                    "motion diagnostics clipped_edges contains an invalid edge",
                )
            bbox = cell.get("alpha_bbox")
            if bbox is not None and (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or any(
                    not isinstance(item, int) or isinstance(item, bool) or item < 0
                    for item in bbox
                )
            ):
                raise EvidenceError(
                    "SCHEMA_INVALID",
                    "motion diagnostics alpha_bbox must be null or four non-negative integers",
                )
            for point_key in ("alpha_centroid", "anchor_offset"):
                point = cell.get(point_key)
                if point is not None and (
                    not isinstance(point, list)
                    or len(point) != 2
                    or any(
                        not isinstance(item, (int, float)) or isinstance(item, bool)
                        for item in point
                    )
                ):
                    raise EvidenceError(
                        "SCHEMA_INVALID",
                        f"motion diagnostics {point_key} must be null or a numeric pair",
                    )
            overflow = _object(
                cell.get("safe_bounds_overflow"),
                "motion diagnostics safe_bounds_overflow",
            )
            _keys(
                overflow,
                {"left_pixels", "top_pixels", "right_pixels", "bottom_pixels"},
                "motion diagnostics safe_bounds_overflow",
            )
            for key in overflow:
                _integer(
                    overflow[key], f"motion diagnostics safe_bounds_overflow.{key}"
                )
            difference = cell.get("pixel_diff_from_previous")
            if difference is not None:
                difference_object = _object(
                    difference, "motion diagnostics pixel_diff_from_previous"
                )
                _keys(
                    difference_object,
                    {"changed_pixels", "rgba_absolute_difference"},
                    "motion diagnostics pixel_diff_from_previous",
                )
                _integer(
                    difference_object["changed_pixels"],
                    "motion diagnostics pixel_diff_from_previous.changed_pixels",
                )
                _integer(
                    difference_object["rgba_absolute_difference"],
                    "motion diagnostics pixel_diff_from_previous.rgba_absolute_difference",
                )
    for index, raw in enumerate(
        _array(value.get("observations"), "motion diagnostics.observations")
    ):
        observation = _object(raw, f"motion diagnostics.observations[{index}]")
        _keys(
            observation,
            {
                "clip_id",
                "cell_index",
                "classification",
                "statement",
                "owner",
                "correction_consequence",
            },
            f"motion diagnostics.observations[{index}]",
        )
        if observation.get("classification") not in {"measured", "observed"}:
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"motion diagnostics.observations[{index}].classification is invalid",
            )
        _string(
            observation.get("clip_id"),
            f"motion diagnostics.observations[{index}].clip_id",
        )
        _integer(
            observation.get("cell_index"),
            f"motion diagnostics.observations[{index}].cell_index",
        )
        _string(
            observation.get("statement"),
            f"motion diagnostics.observations[{index}].statement",
        )
        if observation.get("owner") not in {
            "identity",
            "motion",
            "rendering",
            "assembly",
            "runtime-integration",
            "review-presentation",
            "undetermined",
        }:
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"motion diagnostics.observations[{index}].owner is invalid",
            )
        _string(
            observation.get("correction_consequence"),
            f"motion diagnostics.observations[{index}].correction_consequence",
        )
    if preview_clip_ids != diagnostic_clip_ids:
        raise EvidenceError(
            "SCHEMA_INVALID",
            "motion diagnostics previews must exactly cover diagnostic clips",
        )


def validate_review(value: dict[str, Any]) -> None:
    _keys(
        value,
        {
            "schema_version",
            "review_packet_id",
            "subjects",
            "evidence",
            "reviews",
            "decision",
        },
        "review packet",
    )
    _string(value.get("review_packet_id"), "review packet.review_packet_id")
    subject_ids: set[str] = set()
    for index, raw in enumerate(
        _array(value.get("subjects"), "review packet.subjects")
    ):
        item = _object(raw, f"review packet.subjects[{index}]")
        _keys(
            item, {"id", "schema_version", "sha256"}, f"review packet.subjects[{index}]"
        )
        subject_id = _string(item.get("id"), f"review packet.subjects[{index}].id")
        if subject_id in subject_ids:
            raise EvidenceError(
                "SCHEMA_INVALID", f"duplicate review subject id: {subject_id}"
            )
        subject_ids.add(subject_id)
        _string(
            item.get("schema_version"),
            f"review packet.subjects[{index}].schema_version",
        )
        validate_sha256(item.get("sha256"), f"review packet.subjects[{index}].sha256")
    evidence_ids: set[str] = set()
    evidence_value = _array(value.get("evidence"), "review packet.evidence")
    if not evidence_value:
        raise EvidenceError(
            "APPROVAL_REQUIRED", "review packet evidence must be non-empty"
        )
    for index, raw in enumerate(evidence_value):
        item = _object(raw, f"review packet.evidence[{index}]")
        _keys(item, {"id", "kind", "ref", "sha256"}, f"review packet.evidence[{index}]")
        evidence_id = _string(item.get("id"), f"review packet.evidence[{index}].id")
        if evidence_id in evidence_ids:
            raise EvidenceError(
                "SCHEMA_INVALID", f"duplicate review evidence id: {evidence_id}"
            )
        evidence_ids.add(evidence_id)
        if item.get("kind") not in EVIDENCE_KINDS:
            raise EvidenceError(
                "SCHEMA_INVALID", f"review packet.evidence[{index}].kind is invalid"
            )
        _string(item.get("ref"), f"review packet.evidence[{index}].ref")
        validate_sha256(item.get("sha256"), f"review packet.evidence[{index}].sha256")
    reviews_value = _array(value.get("reviews"), "review packet.reviews")
    if not reviews_value:
        raise EvidenceError(
            "APPROVAL_REQUIRED", "review packet must contain at least one review"
        )
    dispositions: list[str] = []
    for index, raw in enumerate(reviews_value):
        item = _object(raw, f"review packet.reviews[{index}]")
        _keys(
            item,
            {"reviewer", "evidence_ids", "observations"},
            f"review packet.reviews[{index}]",
        )
        _string(item.get("reviewer"), f"review packet.reviews[{index}].reviewer")
        referenced_evidence = _string_array(
            item.get("evidence_ids"), f"review packet.reviews[{index}].evidence_ids"
        )
        if not referenced_evidence:
            raise EvidenceError(
                "APPROVAL_REQUIRED",
                f"review packet.reviews[{index}] must reference evidence",
            )
        if any(evidence_id not in evidence_ids for evidence_id in referenced_evidence):
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"review packet.reviews[{index}] references unknown evidence",
            )
        for observation_index, raw_observation in enumerate(
            _array(
                item.get("observations"), f"review packet.reviews[{index}].observations"
            )
        ):
            observation = _object(
                raw_observation,
                f"review packet.reviews[{index}].observations[{observation_index}]",
            )
            _keys(
                observation,
                {"subject_id", "classification", "disposition", "statement"},
                f"review packet.reviews[{index}].observations[{observation_index}]",
            )
            if observation.get("classification") != "reviewed":
                raise EvidenceError(
                    "SCHEMA_INVALID",
                    "review observations must use classification='reviewed'",
                )
            if observation.get("disposition") not in {
                "acceptable",
                "rework-required",
                "uncertain",
            }:
                raise EvidenceError(
                    "SCHEMA_INVALID", "review observation disposition is invalid"
                )
            if observation.get("subject_id") not in subject_ids:
                raise EvidenceError(
                    "SCHEMA_INVALID", "review observation references an unknown subject"
                )
            dispositions.append(observation["disposition"])
            _string(observation.get("statement"), "review observation.statement")
    decision = _object(value.get("decision"), "review packet.decision")
    _keys(
        decision,
        {"status", "subject_sha256", "reviewer", "evidence"},
        "review packet.decision",
    )
    if decision.get("status") not in {"approved", "rejected"}:
        raise EvidenceError(
            "SCHEMA_INVALID", "review packet.decision.status is invalid"
        )
    validate_sha256(
        decision.get("subject_sha256"), "review packet.decision.subject_sha256"
    )
    expected_decision_hash = canonical_sha256(
        {
            "schema_version": REVIEW_SCHEMA,
            "review_packet_id": value["review_packet_id"],
            "subjects": value["subjects"],
            "evidence": value["evidence"],
            "reviews": value["reviews"],
        },
    )
    if decision["subject_sha256"] != expected_decision_hash:
        raise EvidenceError(
            "APPROVAL_HASH_MISMATCH",
            "review packet decision does not bind subjects, evidence, and reviews",
        )
    _string(decision.get("reviewer"), "review packet.decision.reviewer")
    _string(decision.get("evidence"), "review packet.decision.evidence")
    if not dispositions or any(
        disposition != "acceptable" for disposition in dispositions
    ):
        raise EvidenceError(
            "APPROVAL_REQUIRED",
            "review packet requires non-empty acceptable observations",
        )


def validate_runtime(value: dict[str, Any]) -> None:
    _keys(
        value,
        {
            "schema_version",
            "proof_id",
            "package_manifest_sha256",
            "runtime_contract_sha256",
            "entry_point",
            "viewport",
            "playback",
            "events",
            "rendering",
            "evidence",
            "supplied_by",
        },
        "runtime playback proof",
    )
    _string(value.get("proof_id"), "runtime playback proof.proof_id")
    validate_sha256(
        value.get("package_manifest_sha256"),
        "runtime playback proof.package_manifest_sha256",
    )
    validate_sha256(
        value.get("runtime_contract_sha256"),
        "runtime playback proof.runtime_contract_sha256",
    )
    _string(value.get("entry_point"), "runtime playback proof.entry_point")
    viewport = _object(value.get("viewport"), "runtime playback proof.viewport")
    _keys(
        viewport,
        {"width", "height", "device_pixel_ratio"},
        "runtime playback proof.viewport",
    )
    _integer(viewport.get("width"), "runtime playback proof.viewport.width", minimum=1)
    _integer(
        viewport.get("height"), "runtime playback proof.viewport.height", minimum=1
    )
    if (
        not isinstance(viewport.get("device_pixel_ratio"), (int, float))
        or isinstance(viewport.get("device_pixel_ratio"), bool)
        or not math.isfinite(viewport["device_pixel_ratio"])
        or viewport["device_pixel_ratio"] <= 0
    ):
        raise EvidenceError(
            "SCHEMA_INVALID",
            "runtime playback proof.viewport.device_pixel_ratio must be positive",
        )
    playback = _object(value.get("playback"), "runtime playback proof.playback")
    _keys(
        playback,
        {"clip_ids", "timing_source", "loop_count"},
        "runtime playback proof.playback",
    )
    _string_array(playback.get("clip_ids"), "runtime playback proof.playback.clip_ids")
    _string(
        playback.get("timing_source"), "runtime playback proof.playback.timing_source"
    )
    _integer(
        playback.get("loop_count"),
        "runtime playback proof.playback.loop_count",
        minimum=1,
    )
    for index, raw in enumerate(
        _array(value.get("events"), "runtime playback proof.events")
    ):
        item = _object(raw, f"runtime playback proof.events[{index}]")
        _keys(
            item,
            {"name", "clip_id", "position", "observed"},
            f"runtime playback proof.events[{index}]",
        )
        _string(item.get("name"), f"runtime playback proof.events[{index}].name")
        _string(item.get("clip_id"), f"runtime playback proof.events[{index}].clip_id")
        _integer(
            item.get("position"), f"runtime playback proof.events[{index}].position"
        )
        _boolean(
            item.get("observed"), f"runtime playback proof.events[{index}].observed"
        )
    rendering = _object(value.get("rendering"), "runtime playback proof.rendering")
    _keys(
        rendering,
        {"scale_mode", "alpha_mode", "checks_passed", "observations"},
        "runtime playback proof.rendering",
    )
    _string(rendering.get("scale_mode"), "runtime playback proof.rendering.scale_mode")
    _string(rendering.get("alpha_mode"), "runtime playback proof.rendering.alpha_mode")
    _boolean(
        rendering.get("checks_passed"), "runtime playback proof.rendering.checks_passed"
    )
    _string_array(
        rendering.get("observations"), "runtime playback proof.rendering.observations"
    )
    for index, raw in enumerate(
        _array(value.get("evidence"), "runtime playback proof.evidence")
    ):
        item = _object(raw, f"runtime playback proof.evidence[{index}]")
        _keys(
            item, {"kind", "ref", "sha256"}, f"runtime playback proof.evidence[{index}]"
        )
        if item.get("kind") != "runtime-capture":
            raise EvidenceError(
                "SCHEMA_INVALID",
                "runtime playback proof evidence kind must be runtime-capture",
            )
        _string(item.get("ref"), f"runtime playback proof.evidence[{index}].ref")
        validate_sha256(
            item.get("sha256"), f"runtime playback proof.evidence[{index}].sha256"
        )
    _string(value.get("supplied_by"), "runtime playback proof.supplied_by")


def validate_runtime_projection(value: dict[str, Any]) -> None:
    _keys(
        value,
        {
            "schema_version",
            "package_manifest_sha256",
            "runtime_contract_sha256",
            "contract",
            "assembly",
            "clips",
        },
        "runtime projection",
    )
    validate_sha256(
        value.get("package_manifest_sha256"),
        "runtime projection.package_manifest_sha256",
    )
    validate_sha256(
        value.get("runtime_contract_sha256"),
        "runtime projection.runtime_contract_sha256",
    )
    contract = _object(value.get("contract"), "runtime projection.contract")
    _keys(
        contract,
        {
            "frame_width",
            "frame_height",
            "frame_count",
            "animation_origin",
            "anchor",
            "safe_bounds",
        },
        "runtime projection.contract",
    )
    for key in ("frame_width", "frame_height", "frame_count"):
        _integer(contract.get(key), f"runtime projection.contract.{key}", minimum=1)
    for key, length in (("animation_origin", 2), ("anchor", 2), ("safe_bounds", 4)):
        point = _array(contract.get(key), f"runtime projection.contract.{key}")
        if len(point) != length or any(
            not isinstance(item, int) or isinstance(item, bool) for item in point
        ):
            raise EvidenceError(
                "SCHEMA_INVALID",
                f"runtime projection.contract.{key} must contain {length} integers",
            )
    assembly = _object(value.get("assembly"), "runtime projection.assembly")
    _keys(
        assembly,
        {"sheet", "columns", "rows", "order", "cells"},
        "runtime projection.assembly",
    )
    _string(assembly.get("sheet"), "runtime projection.assembly.sheet")
    _integer(assembly.get("columns"), "runtime projection.assembly.columns", minimum=1)
    _integer(assembly.get("rows"), "runtime projection.assembly.rows", minimum=1)
    if assembly.get("order") not in {"row-major", "column-major"}:
        raise EvidenceError(
            "SCHEMA_INVALID", "runtime projection.assembly.order is invalid"
        )
    for index, raw in enumerate(
        _array(assembly.get("cells"), "runtime projection.assembly.cells")
    ):
        cell = _object(raw, f"runtime projection.assembly.cells[{index}]")
        _keys(
            cell,
            {"source", "repeated_opening", "index", "column", "row"},
            f"runtime projection.assembly.cells[{index}]",
        )
        _string(
            cell.get("source"), f"runtime projection.assembly.cells[{index}].source"
        )
        _boolean(
            cell.get("repeated_opening"),
            f"runtime projection.assembly.cells[{index}].repeated_opening",
        )
        for key in ("index", "column", "row"):
            _integer(cell.get(key), f"runtime projection.assembly.cells[{index}].{key}")
    for index, raw in enumerate(_array(value.get("clips"), "runtime projection.clips")):
        clip = _object(raw, f"runtime projection.clips[{index}]")
        _keys(
            clip,
            {
                "id",
                "frame_ids",
                "durations_ms",
                "events",
                "loop",
                "root_motion",
                "transition",
                "terminal_hold",
            },
            f"runtime projection.clips[{index}]",
        )
        _string(clip.get("id"), f"runtime projection.clips[{index}].id")
        _string_array(
            clip.get("frame_ids"), f"runtime projection.clips[{index}].frame_ids"
        )
        for duration_index, duration in enumerate(
            _array(
                clip.get("durations_ms"),
                f"runtime projection.clips[{index}].durations_ms",
            )
        ):
            _integer(
                duration,
                f"runtime projection.clips[{index}].durations_ms[{duration_index}]",
                minimum=1,
            )
        for event_index, raw_event in enumerate(
            _array(clip.get("events"), f"runtime projection.clips[{index}].events")
        ):
            event = _object(
                raw_event, f"runtime projection.clips[{index}].events[{event_index}]"
            )
            _keys(
                event,
                {"name", "position"},
                f"runtime projection.clips[{index}].events[{event_index}]",
            )
            _string(
                event.get("name"),
                f"runtime projection.clips[{index}].events[{event_index}].name",
            )
            _integer(
                event.get("position"),
                f"runtime projection.clips[{index}].events[{event_index}].position",
            )
        _boolean(clip.get("loop"), f"runtime projection.clips[{index}].loop")
        _string(
            clip.get("root_motion"), f"runtime projection.clips[{index}].root_motion"
        )
        _string(clip.get("transition"), f"runtime projection.clips[{index}].transition")
        _boolean(
            clip.get("terminal_hold"),
            f"runtime projection.clips[{index}].terminal_hold",
        )


def validate_delivery(value: dict[str, Any], *, request: bool = False) -> None:
    fields = {
        "schema_version",
        "job_id",
        "status",
        "identity_bible",
        "motion_blueprints",
        "spacing_plans",
        "pixel_package",
        "motion_diagnostics",
        "review_packet",
        "runtime",
    }
    if not request:
        fields.add("files")
    _keys(
        value,
        fields,
        "delivery",
    )
    _string(value.get("job_id"), "delivery.job_id")
    if value.get("status") not in DELIVERY_STATUSES:
        raise EvidenceError("SCHEMA_INVALID", "delivery.status is invalid")
    _ref(value.get("identity_bible"), "delivery.identity_bible", request=request)
    for index, item in enumerate(
        _array(value.get("motion_blueprints"), "delivery.motion_blueprints")
    ):
        _ref(item, f"delivery.motion_blueprints[{index}]", request=request)
    for index, item in enumerate(
        _array(value.get("spacing_plans"), "delivery.spacing_plans")
    ):
        _ref(item, f"delivery.spacing_plans[{index}]", request=request)
    package = _object(value.get("pixel_package"), "delivery.pixel_package")
    _keys(package, {"manifest", "package_tree_sha256"}, "delivery.pixel_package")
    _ref(package.get("manifest"), "delivery.pixel_package.manifest", request=request)
    validate_sha256(
        package.get("package_tree_sha256"), "delivery.pixel_package.package_tree_sha256"
    )
    _ref(
        value.get("motion_diagnostics"), "delivery.motion_diagnostics", request=request
    )
    _ref(value.get("review_packet"), "delivery.review_packet", request=request)
    runtime = _object(value.get("runtime"), "delivery.runtime")
    _keys(runtime, {"scope", "contract", "projection", "proof"}, "delivery.runtime")
    if runtime.get("scope") not in {"required", "not-requested"}:
        raise EvidenceError("SCHEMA_INVALID", "delivery.runtime.scope is invalid")
    for key in ("contract", "projection", "proof"):
        if runtime.get(key) is not None:
            _ref(runtime[key], f"delivery.runtime.{key}", request=request)
    status = value["status"]
    if status == "package-ready" and runtime.get("scope") != "not-requested":
        raise EvidenceError(
            "STATE_EVIDENCE_MISMATCH",
            "package-ready runtime scope must be not-requested",
        )
    if (
        status in {"runtime-metadata-complete", "runtime-verified"}
        and runtime.get("scope") != "required"
    ):
        raise EvidenceError(
            "STATE_EVIDENCE_MISMATCH", f"{status} runtime scope must be required"
        )
    if status in {"runtime-metadata-complete", "runtime-verified"} and (
        runtime.get("contract") is None or runtime.get("projection") is None
    ):
        raise EvidenceError(
            "STATE_EVIDENCE_MISSING",
            f"{status} requires runtime contract and projection",
        )
    if status == "runtime-verified" and runtime.get("proof") is None:
        raise EvidenceError(
            "STATE_EVIDENCE_MISSING", "runtime-verified requires runtime playback proof"
        )
    if not request:
        seen_files: set[str] = set()
        for index, item in enumerate(_array(value.get("files"), "delivery.files")):
            _ref(item, f"delivery.files[{index}]", request=False)
            if item["ref"] == "delivery.json" or item["ref"] in seen_files:
                raise EvidenceError(
                    "SCHEMA_INVALID",
                    "delivery.files must be unique and exclude delivery.json",
                )
            seen_files.add(item["ref"])


VALIDATORS = {
    IDENTITY_SCHEMA: validate_identity,
    BLUEPRINT_SCHEMA: validate_blueprint,
    SPACING_SCHEMA: validate_spacing,
    DIAGNOSTICS_SCHEMA: validate_diagnostics,
    REVIEW_SCHEMA: validate_review,
    RUNTIME_SCHEMA: validate_runtime,
    RUNTIME_PROJECTION_SCHEMA: validate_runtime_projection,
    DELIVERY_SCHEMA: validate_delivery,
}


def validate_document(
    value: dict[str, Any], expected_schema: str | None = None
) -> None:
    schema = value.get("schema_version")
    if expected_schema is not None and schema != expected_schema:
        raise EvidenceError(
            "SCHEMA_VERSION_UNSUPPORTED", f"schema_version must be {expected_schema!r}"
        )
    validator = VALIDATORS.get(schema)
    if validator is None:
        raise EvidenceError(
            "SCHEMA_VERSION_UNSUPPORTED", f"unsupported schema_version: {schema!r}"
        )
    validator(value)
