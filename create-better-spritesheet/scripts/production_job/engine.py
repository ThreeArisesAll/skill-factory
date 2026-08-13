"""Persistent production state machine and read-only subject verification."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import (
    JOB_SCHEMA,
    RESPONSE_SCHEMA,
    ProductionError,
    validate_intent,
    validate_legacy_topology,
)
from .io import (
    LockedJob,
    atomic_json,
    digest_value,
    freeze_regular,
    read_json,
    sha256_file,
    tree_snapshot,
)
from .legacy import run_legacy

STATE = "state.json"
STATE_KEYS = {"schema_version", "revision", "material_revision", "phase", "intent", "inputs", "approvals", "outputs", "intent_material_sha256", "checkpoint_id", "context_sha256", "checkpoint", "spacing_plan"}
PHASES = {"initializing", "awaiting-canonical-review", "awaiting-production-blueprint-review", "awaiting-keyframe-input", "awaiting-keyframe-review", "awaiting-spacing-plan-input", "awaiting-spacing-plan-review", "awaiting-sequence-input", "awaiting-sequence-review", "awaiting-package-review", "package-ready", "review-complete", "diagnosis-complete"}
GATE_BY_PHASE = {"awaiting-canonical-review": "canonical", "awaiting-production-blueprint-review": "motion-blueprint", "awaiting-keyframe-review": "keyframe-set", "awaiting-spacing-plan-review": "spacing-plan", "awaiting-sequence-review": "sequence", "awaiting-package-review": "package"}


def _failure_point(stage: str) -> None:
    if os.environ.get("SPRITESHEET_PRODUCTION_FAIL_AT") == stage:
        raise ProductionError("INJECTED_FAILURE", "injected production failure", {"stage": stage})


def _checkpoint(state: dict[str, Any]) -> None:
    state["checkpoint_id"] = f"cp-{state['revision']}-{uuid.uuid4().hex[:16]}"
    state.pop("checkpoint", None)
    context = {key: value for key, value in state.items() if key not in {"checkpoint_id", "context_sha256"}}
    phase = state["phase"]
    kind = "input" if phase in {"awaiting-keyframe-input", "awaiting-spacing-plan-input", "awaiting-sequence-input"} else "review" if phase in {"awaiting-canonical-review", "awaiting-production-blueprint-review", "awaiting-keyframe-review", "awaiting-spacing-plan-review", "awaiting-sequence-review", "awaiting-package-review"} else "none"
    questions = {
        "awaiting-canonical-review": "Approve the complete prepared canonical reference set?",
        "awaiting-production-blueprint-review": "Approve the complete identity and motion blueprint?",
        "awaiting-keyframe-input": "Provide one absolute RGBA PNG path for every keyframe position.",
        "awaiting-keyframe-review": "Approve the complete keyframe set?",
        "awaiting-spacing-plan-input": "Provide the complete playback spacing plan.",
        "awaiting-spacing-plan-review": "Approve the complete playback spacing plan?",
        "awaiting-sequence-input": "Provide one absolute RGBA PNG path for every in-between position.",
        "awaiting-sequence-review": "Approve the complete ordered sequence?",
        "awaiting-package-review": "Approve the verified package using the complete diagnostic presentation?",
    }
    payload_properties: dict[str, Any]
    payload_required: list[str]
    if kind == "input":
        if phase == "awaiting-spacing-plan-input":
            bounded_text = {"type": "string", "minLength": 1, "maxLength": 4096}
            bounded_texts = {"type": "array", "maxItems": 256, "items": bounded_text}
            position_schema = {
                "type": "object", "additionalProperties": False,
                "required": ["id", "role", "phase", "events", "spacing", "arc", "contacts", "transition_from_previous", "transition_to_next"],
                "properties": {
                    "id": bounded_text, "role": {"enum": ["keyframe", "in-between"]}, "phase": bounded_text,
                    "events": bounded_texts, "spacing": bounded_text, "arc": bounded_text, "contacts": bounded_texts,
                    "transition_from_previous": bounded_text, "transition_to_next": bounded_text,
                },
            }
            clip_ids = [clip["id"] for clip in state["intent"]["clips"]]
            clip_schema = {
                "type": "object", "additionalProperties": False,
                "required": ["id", "positions", "durations_ms", "events"],
                "properties": {
                    "id": {"enum": clip_ids},
                    "positions": {"type": "array", "minItems": 1, "maxItems": 256, "items": position_schema},
                    "durations_ms": {"type": "array", "minItems": 1, "maxItems": 256, "items": {"type": "integer", "minimum": 1, "maximum": 60000}},
                    "events": {
                        "type": "array", "maxItems": 256,
                        "items": {
                            "type": "object", "additionalProperties": False, "required": ["name", "position"],
                            "properties": {"name": bounded_text, "position": {"type": "integer", "minimum": 0, "maximum": 255}},
                        },
                    },
                },
            }
            payload_properties = {
                "spacing_plan": {
                    "type": "object", "additionalProperties": False, "required": ["clips"],
                    "properties": {"clips": {"type": "array", "minItems": len(clip_ids), "maxItems": len(clip_ids), "items": clip_schema}},
                    "x-spritesheet-constraints": [
                        "clip IDs must be unique and cover the current clip enum exactly once",
                        "position IDs must be unique within a clip",
                        "keyframe IDs and order must match the approved motion blueprint",
                        "durations_ms must have exactly one entry per position and every event.position must index a position",
                        "each clip must contain at least two keyframes and two in-between positions for the current legacy adapter",
                    ],
                }
            }
            payload_required = ["spacing_plan"]
        else:
            role = "keyframe" if phase == "awaiting-keyframe-input" else "in-between"
            expected_ids = sorted(_position_ids(_effective_intent(state), role))
            payload_properties = {
                "assets": {
                    "type": "array", "minItems": len(expected_ids), "maxItems": len(expected_ids),
                    "items": {
                        "type": "object", "additionalProperties": False, "required": ["id", "path"],
                        "properties": {
                            "id": {"enum": expected_ids},
                            "path": {"type": "string", "minLength": 1, "maxLength": 4096, "pattern": "^/"},
                        },
                    },
                    "x-spritesheet-constraints": ["asset IDs must be unique and cover the current enum exactly once"],
                }
            }
            payload_required = ["assets"]
    elif kind == "review":
        payload_properties = {"gate": {"const": GATE_BY_PHASE[phase]}, "decision": {"enum": ["approved", "changes-requested"]}, "authority": {"type": "string", "minLength": 1, "maxLength": 4096}, "evidence": {"type": "string", "minLength": 1, "maxLength": 4096}}
        payload_required = ["gate", "decision", "authority", "evidence"]
        if phase == "awaiting-package-review":
            payload_properties["observations"] = {"type": "array", "minItems": 1, "maxItems": 256, "items": {"type": "object", "additionalProperties": False, "required": ["subject_id", "classification", "disposition", "statement"], "properties": {"subject_id": {"enum": state["outputs"]["package_review_subject_ids"]}, "classification": {"const": "reviewed"}, "disposition": {"const": "acceptable"}, "statement": {"type": "string", "minLength": 1, "maxLength": 4096}}}}
            payload_required.append("observations")
            payload_properties["return_to"] = {"enum": ["keyframes", "spacing-plan", "sequence"]}
    else:
        payload_properties = {}
        payload_required = []
    payload_schema: dict[str, Any] = {"type": "object", "additionalProperties": False, "required": payload_required, "properties": payload_properties}
    if kind == "review" and phase != "awaiting-package-review":
        common_review = {"gate": {"const": GATE_BY_PHASE[phase]}, "authority": payload_properties["authority"], "evidence": payload_properties["evidence"]}
        payload_schema = {"oneOf": [
            {"type": "object", "additionalProperties": False, "required": ["gate", "decision", "authority", "evidence"], "properties": {**common_review, "decision": {"const": "approved"}}},
            {"type": "object", "additionalProperties": False, "required": ["gate", "decision", "authority", "evidence"], "properties": {**common_review, "decision": {"const": "changes-requested"}}},
        ]}
    if phase == "awaiting-package-review":
        subject_ids = state["outputs"]["package_review_subject_ids"]
        observation_base = {"type": "object", "additionalProperties": False, "required": ["subject_id", "classification", "disposition", "statement"], "properties": {"subject_id": {"enum": subject_ids}, "classification": {"const": "reviewed"}, "statement": {"type": "string", "minLength": 1, "maxLength": 4096}}}
        approved_observation = json.loads(json.dumps(observation_base))
        approved_observation["properties"]["disposition"] = {"const": "acceptable"}
        changes_observation = json.loads(json.dumps(observation_base))
        changes_observation["properties"]["disposition"] = {"enum": ["rework-required", "uncertain"]}
        common = {"gate": {"const": "package"}, "authority": payload_properties["authority"], "evidence": payload_properties["evidence"]}
        payload_schema = {"oneOf": [
            {"type": "object", "additionalProperties": False, "required": ["gate", "decision", "authority", "evidence", "observations"], "properties": {**common, "decision": {"const": "approved"}, "observations": {"type": "array", "minItems": len(subject_ids), "maxItems": len(subject_ids), "items": approved_observation}}},
            {"type": "object", "additionalProperties": False, "required": ["gate", "decision", "authority", "evidence", "observations", "return_to"], "properties": {**common, "decision": {"const": "changes-requested"}, "observations": {"type": "array", "minItems": 1, "maxItems": 256, "items": changes_observation}, "return_to": {"enum": ["keyframes", "spacing-plan", "sequence"]}}},
        ]}
    response_schema = None if kind == "none" else {
        "type": "object", "additionalProperties": False,
        "required": ["schema_version", "checkpoint_id", "job_revision", "context_sha256", "kind", "payload"],
        "properties": {
            "schema_version": {"const": RESPONSE_SCHEMA}, "checkpoint_id": {"const": state["checkpoint_id"]},
            "job_revision": {"const": state["revision"]}, "context_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "kind": {"const": kind}, "payload": payload_schema,
        },
    }
    checkpoint_contract = {
        "job_revision": state["revision"], "kind": kind,
        "question": questions.get(phase, "No response is required."),
        "response_schema": response_schema,
        "presentation": _checkpoint_presentation(state, phase),
    }
    state["context_sha256"] = digest_value({"state": context, "checkpoint": checkpoint_contract})
    if response_schema is not None:
        response_schema["properties"]["context_sha256"] = {"const": state["context_sha256"]}
    state["checkpoint"] = {"id": state["checkpoint_id"], "context_sha256": state["context_sha256"], **checkpoint_contract}


def _bound_paths(paths: dict[str, str]) -> list[dict[str, str]]:
    return [{"id": identifier, "path": path, "sha256": sha256_file(Path(path))} for identifier, path in sorted(paths.items())]


def _checkpoint_presentation(state: dict[str, Any], phase: str) -> dict[str, Any]:
    gate = GATE_BY_PHASE.get(phase, phase)
    base: dict[str, Any] = {"phase": phase, "gate": gate, "revision": state["revision"], "assumptions": [], "unresolved_consequences": []}
    if phase == "awaiting-canonical-review":
        identity_content, _ = _draft_evidence_content(state)
        subjects = []
        for item in state["outputs"]["canonical_references"]:
            for kind, key, media_type in (("candidate", "path", "image/png"), ("evidence", "evidence_path", "application/json"), ("proof", "proof_path", "application/json")):
                path = item[key]
                subjects.append({"id": f"{item['id']}-{kind}", "kind": kind, "path": path, "sha256": sha256_file(Path(path)), "media_type": media_type})
        return {**base, "subjects": subjects, "identity_content": identity_content}
    if phase == "awaiting-production-blueprint-review":
        identity_content, blueprint_contents = _draft_evidence_content(state)
        clips = state["intent"]["clips"]
        unresolved = [f"clip {clip['id']} has no supplied action evidence and delegates motion to written intent" for clip in clips if not clip.get("action_evidence")]
        return {**base, "identity_content": identity_content, "blueprint_contents": blueprint_contents, "canonical_references": [{**item, "candidate_sha256": sha256_file(Path(item["path"])), "proof_sha256": sha256_file(Path(item["proof_path"]))} for item in state["outputs"]["canonical_references"]], "unresolved_consequences": unresolved}
    if phase == "awaiting-keyframe-review":
        return {**base, "keyframes": _bound_paths(state["inputs"]["keyframes"])}
    if phase == "awaiting-spacing-plan-review":
        return {**base, "spacing_plan": state["spacing_plan"], "evidence_contents": state["outputs"].get("spacing_plan_drafts", [])}
    if phase == "awaiting-sequence-review":
        return {**base, "keyframes": _bound_paths(state["inputs"]["keyframes"]), "in_betweens": _bound_paths(state["inputs"]["sequence"]), "spacing_plan": state["spacing_plan"]}
    if phase == "awaiting-package-review":
        return {**base, "required_subject_ids": state["outputs"]["package_review_subject_ids"], "subject_sha256": state["outputs"]["package_review_subject_sha256"], "assets": state["outputs"]["package_review_assets"]}
    return {**base, "outputs": state["outputs"]}


def _draft_evidence_content(state: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    intent = state["intent"]
    declarations = intent["identity"]["declarations"]
    canonicals = {item["id"]: item for item in state["outputs"]["canonical_references"]}
    identity_content = {
        "subject": declarations["subject"],
        "canonical_bindings": [{"canonical_id": canonical_id, "direction": next((clip["direction"] for clip in intent["clips"] if clip["identity_source"] == canonical_id), declarations["direction"]), "camera": next((clip["camera"] for clip in intent["clips"] if clip["identity_source"] == canonical_id), declarations["camera"]), "candidate_sha256": sha256_file(Path(record["path"])), "admission_proof_sha256": sha256_file(Path(record["proof_path"]))} for canonical_id, record in canonicals.items()],
        "invariants": [{"id": f"invariant-{index:02d}", "scope": "identity", "statement": statement, "evidence_refs": []} for index, statement in enumerate(declarations["recognition_constraints"], start=1)],
        "allowed_variations": [{"id": f"variation-{index:02d}", "statement": statement} for index, statement in enumerate(declarations.get("allowed_variations", []), start=1)],
        "forbidden_drifts": [{"id": f"drift-{index:02d}", "statement": statement} for index, statement in enumerate(declarations.get("forbidden_drifts", []), start=1)],
    }
    identity_id = f"identity-{state['material_revision']}"
    identity_path = Path(state["outputs"]["identity_bible"]) if state.get("outputs", {}).get("identity_bible") else None
    identity_envelope_hash = sha256_file(identity_path) if identity_path is not None and identity_path.exists() else digest_value({"schema_version": "identity-bible/v1", "identity_id": identity_id, "content": identity_content})
    blueprint_contents = []
    for clip in intent["clips"]:
        positions = [{"frame_id": position["id"], "index": index, "role": position["role"], "phase": position["phase"], "action_beat": position.get("action_beat", position["phase"]), "purpose": position.get("purpose", position["phase"]), "pose": position.get("pose", "declared by reviewed phase"), "orientation": position.get("orientation", clip["direction"]), "projection": position.get("projection", clip["camera"]), "depth_and_occlusion": position.get("depth_and_occlusion", "preserve identity readability"), "root_and_alpha_centroid_intent": position.get("root_and_alpha_centroid_intent", clip["root_motion"]), "contacts": position.get("contacts", []), "transition_from_previous": position.get("transition_from_previous", clip["transition"]), "transition_to_next": position.get("transition_to_next", clip["transition"]), "duration_ms": clip["durations_ms"][index], "events": position.get("events", []), "previous_keyframe": None, "next_keyframe": None} for index, position in enumerate(clip["positions"])]
        blueprint_contents.append({"identity_bible_sha256": identity_envelope_hash, "clip_id": clip["id"], "canonical_id": clip["identity_source"], "intent": clip.get("intent", declarations["art_direction"]), "direction": clip["direction"], "camera": clip["camera"], "entry": clip.get("entry", "declared start"), "exit": clip.get("exit", clip["transition"]), "loop": clip["loop"], "root_motion": clip["root_motion"], "action_evidence": clip.get("action_evidence", []), "positions": positions})
    return identity_content, blueprint_contents


def _validate_state(state: dict[str, Any]) -> None:
    if set(state) - STATE_KEYS or state.get("schema_version") != JOB_SCHEMA or state.get("phase") not in PHASES or type(state.get("revision")) is not int or state["revision"] < 1 or type(state.get("material_revision")) is not int or state["material_revision"] < 1:
        raise ProductionError("JOB_STATE_CORRUPT", "job state fields or phase are invalid")
    checkpoint = state.get("checkpoint")
    if not isinstance(checkpoint, dict) or set(checkpoint) != {"id", "job_revision", "kind", "context_sha256", "question", "response_schema", "presentation"} or checkpoint.get("id") != state.get("checkpoint_id") or checkpoint.get("job_revision") != state.get("revision") or checkpoint.get("context_sha256") != state.get("context_sha256"):
        raise ProductionError("JOB_STATE_CORRUPT", "job checkpoint binding is invalid")
    saved = state["context_sha256"]
    candidate = json.loads(json.dumps(state))
    contract = candidate.pop("checkpoint")
    contract.pop("id", None)
    contract.pop("context_sha256", None)
    candidate.pop("checkpoint_id", None)
    candidate.pop("context_sha256", None)
    response_schema = contract.get("response_schema")
    if response_schema is not None:
        context_property = response_schema.get("properties", {}).get("context_sha256")
        if context_property != {"const": saved}:
            raise ProductionError("JOB_STATE_CORRUPT", "checkpoint response schema does not bind the saved context")
        response_schema["properties"]["context_sha256"] = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    if digest_value({"state": candidate, "checkpoint": contract}) != saved:
        raise ProductionError("JOB_STATE_CORRUPT", "job context hash does not match persisted state")


def _save(job: Path, state: dict[str, Any]) -> None:
    _checkpoint(state)
    _failure_point("state-commit")
    atomic_json(job / STATE, state)


def _new_state(intent: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": JOB_SCHEMA,
        "revision": 1,
        "material_revision": 1,
        "phase": "initializing",
        "intent": intent,
        "inputs": {},
        "approvals": {},
        "outputs": {},
        "intent_material_sha256": _intent_material_digest(intent),
    }


def _intent_source_bindings(intent: dict[str, Any]) -> list[dict[str, str]]:
    sources = intent.get("identity", {}).get("sources", [])
    return [{"id": item["id"], "path": item["path"], "sha256": sha256_file(Path(item["path"]))} for item in sources]


def _intent_material_digest(intent: dict[str, Any]) -> str:
    semantic_intent = {key: value for key, value in intent.items() if key != "base_revision"}
    return digest_value({"intent": semantic_intent, "source_bindings": _intent_source_bindings(intent)})


def _response(value: dict[str, Any], state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if set(value) != {"schema_version", "checkpoint_id", "job_revision", "context_sha256", "kind", "payload"}:
        raise ProductionError("INVALID_CONTRACT", "response contains unsupported or missing fields")
    if value.get("schema_version") != RESPONSE_SCHEMA:
        raise ProductionError("INVALID_CONTRACT", f"response schema_version must be {RESPONSE_SCHEMA!r}")
    if (
        value.get("checkpoint_id") != state.get("checkpoint_id")
        or value.get("job_revision") != state.get("revision")
        or value.get("context_sha256") != state.get("context_sha256")
    ):
        raise ProductionError("STALE_CHECKPOINT", "response does not bind the current checkpoint")
    kind = value.get("kind")
    payload = value.get("payload")
    if kind not in {"input", "review"} or not isinstance(payload, dict):
        raise ProductionError("INVALID_CONTRACT", "response kind and payload are invalid")
    if kind != state.get("checkpoint", {}).get("kind"):
        raise ProductionError("INVALID_CONTRACT", "response kind does not match the current checkpoint")
    return kind, payload


def _artifacts(job: Path, state: dict[str, Any]) -> Path:
    path = job / f"artifacts-r{state['material_revision']}"
    if path.is_symlink():
        raise ProductionError("JOB_STATE_CORRUPT", "artifact revision must not be a symlink")
    return path


def _prepare(job: Path, state: dict[str, Any]) -> None:
    intent = state["intent"]
    artifacts = _artifacts(job, state)
    artifacts.mkdir(parents=True, exist_ok=True)
    canonical_records: list[dict[str, Any]] = []
    for source in intent["identity"]["sources"]:
        request_path = artifacts / f"canonical-{source['id']}-request.json"
        output_path = artifacts / f"canonical-{source['id']}"
        outline = intent["rendering_profile"].get("outline", {"enabled": False, "target_width": "none"})
        atomic_json(request_path, {
            "schema_version": "canonical-authoring-request/v3",
            "canonical_id": source["id"],
            "source": source["path"],
            "target": {
                "frame_width": intent["target"]["frame_width"],
                "frame_height": intent["target"]["frame_height"],
            },
            "outline": outline,
        })
        if not output_path.exists():
            run_legacy("prepare-canonical", "--request", str(request_path), "--output-dir", str(output_path))
        canonical_records.append({
            "id": source["id"],
            "path": str(output_path / "canonical-reference-candidate.png"),
            "evidence_path": str(output_path / "canonical-reference-evidence.json"),
            "proof_path": str(output_path / "canonical-admission-proof.json"),
        })
    state["outputs"].update({
        "canonical_references": canonical_records,
    })
    state["phase"] = "awaiting-canonical-review"


def _approved_evidence(job: Path, state: dict[str, Any], approval: dict[str, Any], *, identity_only: bool = False) -> None:
    from production_evidence.io import write_canonical_json

    artifacts = _artifacts(job, state)
    intent = state["intent"]
    identity_content, blueprint_contents = _draft_evidence_content(state)
    identity_path = artifacts / "identity-bible.json"
    identity_id = f"identity-{state['material_revision']}"
    if identity_only:
        identity_approval = {
            "status": "approved", "subject_sha256": digest_value({"schema_version": "identity-bible/v1", "identity_id": identity_id, "content": identity_content}),
            "reviewer": approval["authority"], "evidence": approval["evidence"],
        }
        write_canonical_json(identity_path, {
            "schema_version": "identity-bible/v1", "identity_id": identity_id,
            "content": identity_content, "approval": identity_approval,
        })
        state["outputs"]["identity_bible"] = str(identity_path)
        return
    identity_sha = sha256_file(identity_path)
    blueprint_paths: list[str] = []
    for clip, draft_content in zip(intent["clips"], blueprint_contents, strict=True):
        content = {**draft_content, "identity_bible_sha256": identity_sha}
        path = artifacts / f"motion-blueprint-{clip['id']}.json"
        blueprint_id = f"{clip['id']}-{state['material_revision']}"
        write_canonical_json(path, {
            "schema_version": "motion-blueprint/v1", "blueprint_id": blueprint_id,
            "content": content,
            "approval": {"status": "approved", "subject_sha256": digest_value({"schema_version": "motion-blueprint/v1", "blueprint_id": blueprint_id, "content": content}), "reviewer": approval["authority"], "evidence": approval["evidence"]},
        })
        blueprint_paths.append(str(path))
    state["outputs"]["identity_bible"] = str(identity_path)
    state["outputs"]["motion_blueprints"] = blueprint_paths


def _expect_review(payload: dict[str, Any], gate: str, allow_spacing: bool = False) -> dict[str, Any]:
    required = {"gate", "decision", "authority", "evidence"}
    allowed = required | ({"spacing_plan"} if allow_spacing else set())
    payload_keys = set(payload)
    if payload_keys != required and (not allow_spacing or payload_keys != allowed):
        raise ProductionError("INVALID_CONTRACT", "review payload contains unsupported or missing fields")
    if payload.get("gate") != gate or payload.get("decision") != "approved":
        raise ProductionError("REVIEW_REQUIRED", f"{gate} requires an explicit approved decision")
    authority = payload.get("authority")
    evidence = payload.get("evidence")
    if not isinstance(authority, str) or not 1 <= len(authority) <= 4096 or not isinstance(evidence, str) or not 1 <= len(evidence) <= 4096:
        raise ProductionError("INVALID_CONTRACT", "review authority and evidence must be strings of 1 to 4096 characters")
    return {
        "gate": gate,
        "decision": "approved",
        "authority": authority,
        "evidence": evidence,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def _apply_spacing_plan(job: Path, state: dict[str, Any], payload: dict[str, Any], approval: dict[str, Any] | None) -> None:
    from production_evidence.io import write_canonical_json

    plan = payload.get("spacing_plan")
    if plan is None:
        raise ProductionError("INVALID_CONTRACT", "keyframe review must include spacing_plan when the blueprint has no in-between positions")
    if not isinstance(plan, dict) or set(plan) != {"clips"} or not isinstance(plan["clips"], list) or not 1 <= len(plan["clips"]) <= 256:
        raise ProductionError("INVALID_CONTRACT", "spacing_plan must contain only a clips array")
    planned: dict[str, dict[str, Any]] = {}
    source_clips = {clip["id"]: clip for clip in state["intent"]["clips"]}
    for raw in plan["clips"]:
        if not isinstance(raw, dict) or set(raw) != {"id", "positions", "durations_ms", "events"}:
            raise ProductionError("INVALID_CONTRACT", "each spacing-plan clip must contain id, positions, durations_ms, and events")
        clip_id = raw.get("id")
        positions = raw.get("positions")
        if clip_id not in source_clips or clip_id in planned or not isinstance(positions, list):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan clip IDs or positions are invalid")
        spacing_keys = {"id", "role", "phase", "events", "spacing", "arc", "contacts", "transition_from_previous", "transition_to_next"}
        if not 1 <= len(positions) <= 256 or any(not isinstance(position, dict) or set(position) != spacing_keys or position.get("role") not in {"keyframe", "in-between"} for position in positions):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan positions must provide every reviewed spacing semantic field")
        text_fields = ("id", "phase", "spacing", "arc", "transition_from_previous", "transition_to_next")
        if any(
            any(not isinstance(position.get(key), str) or not 1 <= len(position[key]) <= 4096 for key in text_fields)
            or any(
                not isinstance(position.get(key), list)
                or len(position[key]) > 256
                or any(not isinstance(value, str) or not 1 <= len(value) <= 4096 for value in position[key])
                for key in ("events", "contacts")
            )
            for position in positions
        ):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan semantic strings and lists exceed the closed bounds")
        position_ids = [position.get("id") for position in positions]
        if len(position_ids) != len(positions) or len(set(position_ids)) != len(position_ids):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan position IDs must be unique")
        key_ids = [position["id"] for position in source_clips[clip_id]["positions"] if position["role"] == "keyframe"]
        if [position.get("id") for position in positions if position.get("role") == "keyframe"] != key_ids:
            raise ProductionError("INVALID_CONTRACT", "spacing plan must preserve the approved keyframe order")
        if sum(position.get("role") == "in-between" for position in positions) < 2:
            raise ProductionError("LEGACY_TOPOLOGY_UNSUPPORTED", "the installed v4 adapter requires at least two in-between positions")
        durations = raw.get("durations_ms")
        if not isinstance(durations, list) or len(durations) != len(positions) or any(type(value) is not int or not 1 <= value <= 60000 for value in durations):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan durations must match positions")
        if (
            not isinstance(raw.get("events"), list)
            or any(
                not isinstance(event, dict)
                or set(event) != {"name", "position"}
                or not isinstance(event.get("name"), str)
                or not 1 <= len(event["name"]) <= 4096
                or type(event.get("position")) is not int
                or not 0 <= event["position"] < len(positions)
                for event in raw["events"]
            )
        ):
            raise ProductionError("INVALID_CONTRACT", "spacing-plan events must be closed named position records")
        planned[clip_id] = dict(raw)
    if set(planned) != set(source_clips):
        raise ProductionError("INVALID_CONTRACT", "spacing plan must cover every clip exactly once")
    state["spacing_plan"] = planned
    effective_blueprints = dict(zip(source_clips, state["outputs"]["motion_blueprints"], strict=True))
    keyframes = state["inputs"]["keyframes"]
    spacing_paths: list[str] = []
    spacing_drafts: list[dict[str, Any]] = []
    for clip_index, clip in enumerate(plan["clips"]):
        clip_key_ids = {position["id"] for position in source_clips[clip["id"]]["positions"]}
        content = {
            "motion_blueprint_sha256": sha256_file(Path(effective_blueprints[clip["id"]])),
            "clip_id": clip["id"],
            "approved_keyframes": [{"frame_id": frame_id, "source_sha256": sha256_file(Path(path))} for frame_id, path in sorted(keyframes.items()) if frame_id in clip_key_ids],
            "positions": [
                {
                    "frame_id": position["id"], "index": index, "role": position["role"],
                    "previous_keyframe": _derive_brackets(clip["positions"], index, False)[0] if position["role"] == "in-between" else None,
                    "next_keyframe": _derive_brackets(clip["positions"], index, False)[1] if position["role"] == "in-between" else None,
                    "duration_ms": clip["durations_ms"][index], "events": position["events"], "spacing": position["spacing"],
                    "arc": position["arc"], "contacts": position["contacts"], "transition_from_previous": position["transition_from_previous"], "transition_to_next": position["transition_to_next"],
                }
                for index, position in enumerate(clip["positions"])
            ],
        }
        spacing_id = f"spacing-{clip_index:04d}-r{state['material_revision']}"
        spacing_drafts.append(content)
        if approval is None:
            continue
        spacing_path = _artifacts(job, state) / f"spacing-plan-{clip_index:04d}.json"
        write_canonical_json(spacing_path, {
            "schema_version": "spacing-plan/v1", "spacing_plan_id": spacing_id, "content": content,
            "approval": {"status": "approved", "subject_sha256": digest_value({"schema_version": "spacing-plan/v1", "spacing_plan_id": spacing_id, "content": content}), "reviewer": approval["authority"], "evidence": approval["evidence"]},
        })
        spacing_paths.append(str(spacing_path))
    state["outputs"]["spacing_plan_drafts"] = spacing_drafts
    if approval is not None:
        state["outputs"]["spacing_plans"] = spacing_paths


def _effective_intent(state: dict[str, Any]) -> dict[str, Any]:
    intent = json.loads(json.dumps(state["intent"]))
    planned = state.get("spacing_plan", {})
    for clip in intent.get("clips", []):
        if clip["id"] in planned:
            clip.update({key: planned[clip["id"]][key] for key in ("positions", "durations_ms", "events")})
    return intent


def _expect_assets(job: Path, state: dict[str, Any], payload: dict[str, Any], expected_ids: set[str]) -> dict[str, str]:
    if set(payload) != {"assets"}:
        raise ProductionError("INVALID_CONTRACT", "input payload contains unsupported or missing fields")
    assets = payload.get("assets")
    if not isinstance(assets, list) or len(assets) != len(expected_ids):
        raise ProductionError("INVALID_CONTRACT", "input payload.assets must exactly cover the expected asset count")
    mapped: dict[str, str] = {}
    for index, raw in enumerate(assets):
        if not isinstance(raw, dict) or set(raw) != {"id", "path"}:
            raise ProductionError("INVALID_CONTRACT", f"assets[{index}] must contain only id and path")
        if not isinstance(raw["id"], str) or not isinstance(raw["path"], str) or not 1 <= len(raw["path"]) <= 4096:
            raise ProductionError("INVALID_CONTRACT", f"assets[{index}] id and path must be bounded strings")
        path = Path(raw["path"])
        if raw["id"] in mapped or raw["id"] not in expected_ids or not path.is_absolute():
            raise ProductionError("INVALID_CONTRACT", f"assets[{index}] is not an expected readable absolute file")
        frozen_dir = _artifacts(job, state) / "frozen-inputs"
        try:
            mapped[str(raw["id"])] = freeze_regular(path, frozen_dir)
        except (OSError, ValueError) as error:
            raise ProductionError("INVALID_INPUT_FILE", "asset could not be frozen safely") from error
    if set(mapped) != expected_ids:
        raise ProductionError("INVALID_CONTRACT", "input assets do not exactly cover the requested positions")
    return mapped


def _position_ids(intent: dict[str, Any], role: str) -> set[str]:
    return {position["id"] for clip in intent["clips"] for position in clip["positions"] if position["role"] == role}


def _derive_brackets(positions: list[dict[str, Any]], index: int, loop: bool = False) -> tuple[str, str]:
    previous = next((item["id"] for item in reversed(positions[:index]) if item["role"] == "keyframe"), None)
    following = next((item["id"] for item in positions[index + 1:] if item["role"] == "keyframe"), None)
    if loop and previous is None:
        previous = next((item["id"] for item in reversed(positions) if item["role"] == "keyframe"), None)
    if loop and following is None:
        following = next((item["id"] for item in positions if item["role"] == "keyframe"), None)
    if previous is None or following is None:
        raise ProductionError("LEGACY_TOPOLOGY_UNSUPPORTED", "the v4 adapter requires each in-between to lie between approved keyframes")
    return previous, following


def _legacy_request(state: dict[str, Any]) -> dict[str, Any]:
    intent = _effective_intent(state)
    validate_legacy_topology(intent)
    paths = {**state["inputs"]["keyframes"], **state["inputs"]["sequence"]}
    canonical = {item["id"]: item for item in state["outputs"]["canonical_references"]}
    source_hashes = {artifact_id: sha256_file(Path(path)) for artifact_id, path in paths.items()}
    canonical_hashes = {item_id: sha256_file(Path(item["path"])) for item_id, item in canonical.items()}
    admission_hashes = {item_id: sha256_file(Path(item["proof_path"])) for item_id, item in canonical.items()}
    clips: list[dict[str, Any]] = []
    for clip in intent["clips"]:
        frames: list[dict[str, Any]] = []
        for index, position in enumerate(clip["positions"]):
            frame = {"id": position["id"], "role": position["role"], "source_path": paths[position["id"]]}
            if position["role"] == "in-between":
                frame["previous_keyframe"], frame["next_keyframe"] = _derive_brackets(clip["positions"], index, clip["loop"])
            frames.append(frame)
        clips.append({
            "id": clip["id"], "canonical_reference": clip["identity_source"],
            "direction": clip["direction"], "camera": clip["camera"], "loop": clip["loop"],
            "repeat_opening_cell": clip["loop"], "root_motion": clip["root_motion"],
            "transition": clip["transition"], "terminal_hold": clip["terminal_hold"],
            "durations_ms": clip["durations_ms"] + ([clip["durations_ms"][0]] if clip["loop"] else []),
            "events": clip["events"], "frames": frames,
        })
    approvals = state["approvals"]
    reviews: list[dict[str, Any]] = []
    order = 1
    for canonical_id in canonical:
        approval = approvals["canonical"]
        reviews.append(_review_record(
            f"canonical-review-{canonical_id}", "canonical-approval", [canonical_id],
            canonical_hashes, admission_hashes, approval["authority"], approval["evidence"], order,
        ))
        order += 1
    for clip in intent["clips"]:
        canonical_id = clip["identity_source"]
        key_ids = [position["id"] for position in clip["positions"] if position["role"] == "keyframe"]
        approval = approvals["keyframes"]
        reviews.append(_review_record(
            f"keyframe-review-{clip['id']}", "keyframe-set-approval", [canonical_id, *key_ids],
            {**canonical_hashes, **source_hashes}, admission_hashes,
            approval["authority"], approval["evidence"], order,
        ))
        order += 1
    for clip in intent["clips"]:
        canonical_id = clip["identity_source"]
        frame_ids = [position["id"] for position in clip["positions"]]
        approval = approvals["sequence"]
        reviews.append(_review_record(
            f"sequence-review-{clip['id']}", "sequence-approval", [canonical_id, *frame_ids],
            {**canonical_hashes, **source_hashes}, admission_hashes,
            approval["authority"], approval["evidence"], order,
        ))
        order += 1
    target = intent["target"]
    frame_count = sum(len(clip["positions"]) + int(clip["loop"]) for clip in intent["clips"])
    return {
        "schema_version": "spritesheet-production-request/v4",
        "contract": {
            "frame_width": target["frame_width"], "frame_height": target["frame_height"],
            "frame_count": frame_count, "high_resolution_short_side": 512,
            "sampler": "lanczos-premultiplied-v1",
            "outline": intent["rendering_profile"].get("outline", {"enabled": False, "target_width": "none"}),
            "animation_origin": target["animation_origin"], "anchor": target["anchor"], "safe_bounds": target["safe_bounds"],
        },
        "canonical_references": list(canonical.values()), "clips": clips, "reviews": reviews,
        "grid": {"columns": target.get("columns", min(frame_count, 8)), "order": "row-major"},
    }


def _review_record(review_id: str, gate: str, ids: list[str], hashes: dict[str, str], admissions: dict[str, str], reviewer: str, evidence: str, order: int) -> dict[str, Any]:
    return {
        "id": review_id, "gate": gate, "subject_ids": ids,
        "subject_sha256": {item_id: hashes[item_id] for item_id in ids},
        "reviewer": reviewer, "evidence": evidence, "declared_order": order,
        "admission_sha256": {item_id: admissions[item_id] for item_id in ids if item_id in admissions},
    }


def _build(job: Path, state: dict[str, Any]) -> None:
    artifacts = _artifacts(job, state)
    request_path = artifacts / "production-request-v4.json"
    package_path = artifacts / "package"
    staging = Path(tempfile.mkdtemp(prefix=".production-build-", dir=job))
    staged_request = staging / "production-request-v4.json"
    staged_package = staging / "package"
    try:
        atomic_json(staged_request, _legacy_request(state))
        run_legacy("build-package", "--request", str(staged_request), "--output-dir", str(staged_package))
        run_legacy("verify-package", "--manifest", str(staged_package / "manifest.json"))
        _failure_point("build")
        os.replace(staged_request, request_path)
        os.replace(staged_package, package_path)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    state["outputs"].update({"production_request": str(request_path), "package_manifest": str(package_path / "manifest.json")})
    diagnostics = artifacts / "diagnostics"
    adapter = Path(__file__).parents[1] / "spritesheet_delivery.py"
    completed = subprocess.run([sys.executable, str(adapter), "diagnose", "--manifest", str(package_path / "manifest.json"), "--output-dir", str(diagnostics)], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise ProductionError("DELIVERY_ADAPTER_FAILED", "diagnostics adapter failed", {"adapter": "diagnostics"})
    _failure_point("diagnostics")
    state["outputs"]["diagnostics"] = str(diagnostics / "motion-diagnostics.json")
    diagnostic_document = read_json(diagnostics / "motion-diagnostics.json")
    presentation_refs = [item["ref"] for item in diagnostic_document["assets"].values()]
    presentation_refs.extend(item["asset"]["ref"] for item in diagnostic_document["previews"])
    state["outputs"]["review_presentation"] = [str(diagnostics / reference) for reference in presentation_refs]
    state["outputs"]["package_review_sha256"] = {
        "manifest": sha256_file(package_path / "manifest.json"),
        "diagnostics": sha256_file(diagnostics / "motion-diagnostics.json"),
        **{reference: sha256_file(diagnostics / reference) for reference in presentation_refs},
    }
    subject_hashes = {
        "identity": sha256_file(Path(state["outputs"]["identity_bible"])),
        **{f"blueprint-{index}": sha256_file(Path(path)) for index, path in enumerate(state["outputs"]["motion_blueprints"])},
        **{f"spacing-{index}": sha256_file(Path(path)) for index, path in enumerate(state["outputs"]["spacing_plans"])},
        "diagnostics": sha256_file(diagnostics / "motion-diagnostics.json"),
        "package": sha256_file(package_path / "manifest.json"),
    }
    state["outputs"]["package_review_subject_ids"] = list(subject_hashes)
    state["outputs"]["package_review_subject_sha256"] = subject_hashes
    state["outputs"]["package_review_assets"] = [
        {"id": "manifest", "path": str(package_path / "manifest.json"), "sha256": subject_hashes["package"], "media_type": "application/json"},
        {"id": "diagnostics", "path": str(diagnostics / "motion-diagnostics.json"), "sha256": subject_hashes["diagnostics"], "media_type": "application/json"},
        *[{"id": f"presentation-{index:04d}", "path": path, "sha256": sha256_file(Path(path)), "media_type": "image/gif" if Path(path).suffix == ".gif" else "image/png"} for index, path in enumerate(state["outputs"]["review_presentation"])],
    ]
    state["phase"] = "awaiting-package-review"


def _seal_delivery(job: Path, state: dict[str, Any]) -> None:
    """Project approved job evidence through the delivery module's narrow CLI."""
    from production_evidence.io import package_tree_sha256, write_canonical_json
    from production_evidence.schemas import validate_document

    adapter = Path(__file__).parents[1] / "spritesheet_delivery.py"
    artifacts = _artifacts(job, state)
    manifest = Path(state["outputs"]["package_manifest"])
    diagnostics = Path(state["outputs"]["diagnostics"])
    approval = state["approvals"]["package"]
    validate_document(read_json(Path(state["outputs"]["identity_bible"])))
    current_bindings = {
        "manifest": sha256_file(manifest),
        "diagnostics": sha256_file(diagnostics),
        **{Path(path).relative_to(diagnostics.parent).as_posix().removeprefix("diagnostics/"): sha256_file(Path(path)) for path in state["outputs"]["review_presentation"]},
    }
    if current_bindings != state["outputs"].get("package_review_sha256"):
        raise ProductionError("STALE_CHECKPOINT", "package review subjects changed after presentation")
    subjects = []
    for identifier, schema, path in [
        ("identity", "identity-bible/v1", Path(state["outputs"]["identity_bible"])),
        *[(f"blueprint-{index}", "motion-blueprint/v1", Path(path)) for index, path in enumerate(state["outputs"]["motion_blueprints"])],
        *[(f"spacing-{index}", "spacing-plan/v1", Path(path)) for index, path in enumerate(state["outputs"]["spacing_plans"])],
        ("diagnostics", "motion-diagnostics/v1", diagnostics),
        ("package", "spritesheet-package/v4", manifest),
    ]:
        subjects.append({"id": identifier, "schema_version": schema, "sha256": sha256_file(path)})
    evidence = []
    for path_value in state["outputs"]["review_presentation"]:
        path = Path(path_value)
        kinds = {"contact-sheet": "contact-sheet", "native-size-board": "native-size-frame", "onion-skin": "onion-skin"}
        kind = kinds.get(path.stem, "loop-capture")
        evidence.append({"id": f"presentation-{len(evidence):04d}", "kind": kind, "ref": path.relative_to(artifacts).as_posix(), "sha256": sha256_file(path)})
    observations = list(approval["observations"])
    reviews = [{"reviewer": approval["authority"], "evidence_ids": [item["id"] for item in evidence], "observations": observations}]
    review_id = f"review-r{state['material_revision']}"
    review_subject = {"schema_version": "review-packet/v1", "review_packet_id": review_id, "subjects": subjects, "evidence": evidence, "reviews": reviews}
    review = {**review_subject, "decision": {"status": "approved", "subject_sha256": digest_value(review_subject), "reviewer": approval["authority"], "evidence": approval["evidence"]}}
    review_path = artifacts / "review-packet.json"
    write_canonical_json(review_path, review)
    request = {"schema_version": "spritesheet-production-delivery/v1", "job_id": job.name, "status": "package-ready", "identity_bible": {"path": state["outputs"]["identity_bible"], "sha256": sha256_file(Path(state["outputs"]["identity_bible"]))}, "motion_blueprints": [{"path": path, "sha256": sha256_file(Path(path))} for path in state["outputs"]["motion_blueprints"]], "spacing_plans": [{"path": path, "sha256": sha256_file(Path(path))} for path in state["outputs"]["spacing_plans"]], "pixel_package": {"manifest": {"path": str(manifest), "sha256": sha256_file(manifest)}, "package_tree_sha256": package_tree_sha256(manifest.parent)}, "motion_diagnostics": {"path": str(diagnostics), "sha256": sha256_file(diagnostics)}, "review_packet": {"path": str(review_path), "sha256": sha256_file(review_path)}, "runtime": {"scope": "not-requested", "contract": None, "projection": None, "proof": None}}
    request_path = artifacts / "delivery-request.json"
    write_canonical_json(request_path, request)
    output = Path(state["intent"]["output_scope"].get("delivery_dir", artifacts / "sealed-delivery"))
    completed = subprocess.run([sys.executable, str(adapter), "seal-delivery", "--request", str(request_path), "--output-dir", str(output)], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise ProductionError("DELIVERY_ADAPTER_FAILED", "delivery sealing failed", {"adapter": "seal-delivery"})
    completed = subprocess.run([sys.executable, str(adapter), "verify", "--delivery", str(output / "delivery.json")], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise ProductionError("DELIVERY_VERIFICATION_FAILED", "sealed delivery failed verification", {"adapter": "delivery-verify"})
    state["outputs"]["sealed_delivery"] = str(output / "delivery.json")
    state["outputs"]["delivery_state"] = "package-ready"
    state["phase"] = "package-ready"


def _read_only_job(job: Path, state: dict[str, Any]) -> None:
    subject = Path(state["intent"]["output_scope"]["subject"])
    before = tree_snapshot(subject)
    verification = verify_subject(subject)
    diagnostics_result: dict[str, Any] | None = None
    if state["intent"]["mode"] == "diagnose":
        manifest = subject / "manifest.json" if subject.is_dir() else subject
        diagnostics_dir = _artifacts(job, state) / "diagnostics"
        adapter = Path(__file__).parents[1] / "spritesheet_delivery.py"
        completed = subprocess.run([sys.executable, str(adapter), "diagnose", "--manifest", str(manifest), "--output-dir", str(diagnostics_dir)], check=False, capture_output=True, text=True)
        if completed.returncode:
            raise ProductionError("DELIVERY_ADAPTER_FAILED", "diagnostics adapter failed", {"adapter": "diagnostics"})
        document = read_json(diagnostics_dir / "motion-diagnostics.json")
        refs = [item["ref"] for item in document["assets"].values()]
        refs.extend(item["asset"]["ref"] for item in document["previews"])
        diagnostics_result = {
            "classification": "SUPPLIED",
            "document": {"path": str(diagnostics_dir / "motion-diagnostics.json"), "sha256": sha256_file(diagnostics_dir / "motion-diagnostics.json")},
            "presentation": [{"path": str(diagnostics_dir / reference), "sha256": sha256_file(diagnostics_dir / reference)} for reference in refs],
        }
    after = tree_snapshot(subject)
    if before != after:
        raise ProductionError("READ_ONLY_VIOLATION", "subject changed during read-only inspection")
    report_path = _artifacts(job, state) / "inspection-report.json"
    atomic_json(report_path, {
        "schema_version": "spritesheet-production-inspection/v1",
        "mode": state["intent"]["mode"], "subject": str(subject),
        "before": before, "after": after, "verification": verification,
        "diagnostics": diagnostics_result,
    })
    state["outputs"]["report"] = str(report_path)
    if diagnostics_result is not None:
        state["outputs"]["diagnostics"] = diagnostics_result
    state["phase"] = "review-complete" if state["intent"]["mode"] == "review" else "diagnosis-complete"


def _apply_response(job: Path, state: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    phase = state["phase"]
    intent = state["intent"]
    if kind == "review" and payload.get("decision") == "changes-requested":
        expected = {"gate", "decision", "authority", "evidence", "observations", "return_to"} if phase == "awaiting-package-review" else {"gate", "decision", "authority", "evidence"}
        if set(payload) != expected or payload.get("gate") != GATE_BY_PHASE.get(phase) or not all(isinstance(payload.get(key), str) and 1 <= len(payload[key]) <= 4096 for key in ("gate", "authority", "evidence")):
            raise ProductionError("INVALID_CONTRACT", "changes-requested review must use the closed review shape")
        if "observations" in expected:
            observations = payload["observations"]
            required = state["outputs"]["package_review_subject_ids"]
            if not isinstance(observations, list) or not observations or any(not isinstance(item, dict) or set(item) != {"subject_id", "classification", "disposition", "statement"} or item.get("subject_id") not in required or item.get("classification") != "reviewed" or item.get("disposition") not in {"rework-required", "uncertain"} or not isinstance(item.get("statement"), str) or not 1 <= len(item["statement"]) <= 4096 for item in observations):
                raise ProductionError("INVALID_CONTRACT", "package changes require reviewed rework-required or uncertain observations")
            identifiers = [item["subject_id"] for item in observations]
            if len(identifiers) != len(set(identifiers)):
                raise ProductionError("INVALID_CONTRACT", "package change observations must not duplicate subjects")
        state["approvals"][f"{phase}-changes-requested"] = {"authority": payload["authority"], "evidence": payload["evidence"], "decision": "changes-requested"}
        if phase == "awaiting-keyframe-review":
            state["inputs"].pop("keyframes", None)
            state["phase"] = "awaiting-keyframe-input"
        elif phase == "awaiting-spacing-plan-review":
            state.pop("spacing_plan", None)
            state["outputs"].pop("spacing_plans", None)
            state["phase"] = "awaiting-spacing-plan-input"
        elif phase == "awaiting-sequence-review":
            state["inputs"].pop("sequence", None)
            state["phase"] = "awaiting-sequence-input"
        elif phase == "awaiting-package-review":
            return_to = payload.get("return_to")
            routes = {"keyframes": "awaiting-keyframe-input", "spacing-plan": "awaiting-spacing-plan-input", "sequence": "awaiting-sequence-input"}
            if return_to not in routes:
                raise ProductionError("INVALID_CONTRACT", "package changes-requested requires return_to keyframes, spacing-plan, or sequence")
            _reopen_package_rework(state, return_to, routes[return_to])
        return
    if phase == "awaiting-canonical-review" and kind == "review":
        approval = _expect_review(payload, "canonical")
        state["approvals"]["canonical"] = approval
        state["job_path"] = str(job)
        _approved_evidence(job, state, approval, identity_only=True)
        state.pop("job_path", None)
        state["phase"] = "awaiting-production-blueprint-review"
    elif phase == "awaiting-production-blueprint-review" and kind == "review":
        approval = _expect_review(payload, "motion-blueprint")
        state["approvals"]["motion-blueprint"] = approval
        state["job_path"] = str(job)
        _approved_evidence(job, state, approval)
        state.pop("job_path", None)
        state["phase"] = "awaiting-keyframe-input"
    elif phase == "awaiting-keyframe-input" and kind == "input":
        state["inputs"]["keyframes"] = _expect_assets(job, state, payload, _position_ids(intent, "keyframe"))
        state["phase"] = "awaiting-keyframe-review"
    elif phase == "awaiting-keyframe-review" and kind == "review":
        approval = _expect_review(payload, "keyframe-set")
        state["approvals"]["keyframes"] = approval
        state["phase"] = "awaiting-spacing-plan-input"
    elif phase == "awaiting-spacing-plan-input" and kind == "input":
        if set(payload) != {"spacing_plan"}:
            raise ProductionError("INVALID_CONTRACT", "spacing plan input contains unsupported or missing fields")
        _apply_spacing_plan(job, state, payload, None)
        state["phase"] = "awaiting-spacing-plan-review"
    elif phase == "awaiting-spacing-plan-review" and kind == "review":
        approval = _expect_review(payload, "spacing-plan")
        state["approvals"]["spacing-plan"] = approval
        _apply_spacing_plan(job, state, {"spacing_plan": {"clips": list(state["spacing_plan"].values())}}, approval)
        state["phase"] = "awaiting-sequence-input"
    elif phase == "awaiting-sequence-input" and kind == "input":
        state["inputs"]["sequence"] = _expect_assets(job, state, payload, _position_ids(_effective_intent(state), "in-between"))
        state["phase"] = "awaiting-sequence-review"
    elif phase == "awaiting-sequence-review" and kind == "review":
        state["approvals"]["sequence"] = _expect_review(payload, "sequence")
        _build(job, state)
    elif phase == "awaiting-package-review" and kind == "review":
        if set(payload) != {"gate", "decision", "authority", "evidence", "observations"} or payload.get("gate") != "package" or payload.get("decision") != "approved" or not isinstance(payload.get("observations"), list) or not all(isinstance(payload.get(key), str) and 1 <= len(payload[key]) <= 4096 for key in ("authority", "evidence")):
            raise ProductionError("INVALID_CONTRACT", "package review must provide a closed approved decision and observations")
        observations = payload["observations"]
        required = state["outputs"]["package_review_subject_ids"]
        if any(not isinstance(item, dict) or set(item) != {"subject_id", "classification", "disposition", "statement"} or item.get("classification") != "reviewed" or item.get("disposition") != "acceptable" or not isinstance(item.get("statement"), str) or not 1 <= len(item["statement"]) <= 4096 for item in observations):
            raise ProductionError("INVALID_CONTRACT", "package observations must be closed acceptable reviewed records")
        identifiers = [item["subject_id"] for item in observations]
        if len(identifiers) != len(set(identifiers)) or set(identifiers) != set(required):
            raise ProductionError("REVIEW_COVERAGE_MISMATCH", "package observations must cover every required subject exactly once")
        state["approvals"]["package"] = {"authority": payload["authority"], "evidence": payload["evidence"], "observations": observations}
        _seal_delivery(job, state)
    else:
        raise ProductionError("UNEXPECTED_RESPONSE", f"{kind} response is not valid in phase {phase!r}")


def _reopen_package_rework(state: dict[str, Any], return_to: str, phase: str) -> None:
    """Open an immutable material lineage while retaining only approved upstream evidence."""
    base_output_keys = {"canonical_references", "identity_bible", "motion_blueprints"}
    output_keys = set(base_output_keys)
    input_keys: set[str] = set()
    approval_keys = {"canonical", "motion-blueprint"}
    keep_spacing = return_to == "sequence"
    if return_to in {"spacing-plan", "sequence"}:
        input_keys.add("keyframes")
        approval_keys.add("keyframes")
    if keep_spacing:
        output_keys.update({"spacing_plan_drafts", "spacing_plans"})
        approval_keys.add("spacing-plan")
    approval_keys.update(key for key in state["approvals"] if key.endswith("-changes-requested"))
    state["material_revision"] += 1
    state["outputs"] = {key: value for key, value in state["outputs"].items() if key in output_keys}
    state["inputs"] = {key: value for key, value in state["inputs"].items() if key in input_keys}
    state["approvals"] = {key: value for key, value in state["approvals"].items() if key in approval_keys}
    if not keep_spacing:
        state.pop("spacing_plan", None)
    state["phase"] = phase


def _update_intent(job: Path, state: dict[str, Any], intent: dict[str, Any]) -> None:
    old = state["intent"]
    new_material = _intent_material_digest(intent)
    if state.get("intent_material_sha256") == new_material:
        return
    old_semantic = {key: value for key, value in old.items() if key != "base_revision"}
    identity_changed = old.get("identity") != intent.get("identity")
    target_changed = old.get("target") != intent.get("target")
    profile_changed = old.get("rendering_profile") != intent.get("rendering_profile")
    clips_changed = old.get("clips") != intent.get("clips")
    old_clip_bindings = [
        {key: clip.get(key) for key in ("id", "identity_source", "direction", "camera")}
        for clip in old.get("clips", [])
    ]
    new_clip_bindings = [
        {key: clip.get(key) for key in ("id", "identity_source", "direction", "camera")}
        for clip in intent.get("clips", [])
    ]
    clip_identity_binding_changed = old_clip_bindings != new_clip_bindings
    output_changed = old.get("output_scope") != intent.get("output_scope")
    stored_bindings = state.get("intent_material_sha256")
    old_semantic_with_current_bindings = digest_value({"intent": old_semantic, "source_bindings": _intent_source_bindings(intent)})
    source_bytes_changed = stored_bindings != old_semantic_with_current_bindings
    state["revision"] += 1
    state["intent"] = intent
    state["intent_material_sha256"] = new_material
    if source_bytes_changed or identity_changed or target_changed or profile_changed or clip_identity_binding_changed:
        state["material_revision"] += 1
        state["inputs"] = {}
        state["approvals"] = {}
        state["outputs"] = {}
        state["phase"] = "initializing"
    elif clips_changed:
        state["material_revision"] += 1
        preserved_outputs = {key: state["outputs"][key] for key in ("canonical_references", "identity_bible") if key in state["outputs"]}
        preserved_approvals = {key: state["approvals"][key] for key in ("canonical",) if key in state["approvals"]}
        state["inputs"] = {}
        state["approvals"] = preserved_approvals
        state["outputs"] = preserved_outputs
        state.pop("spacing_plan", None)
        state["phase"] = "awaiting-production-blueprint-review"
    elif output_changed or old.get("runtime_scope") != intent.get("runtime_scope"):
        state["outputs"].pop("sealed_delivery", None)
        state["outputs"].pop("delivery_state", None)
        if "package_manifest" in state["outputs"]:
            state["phase"] = "awaiting-package-review"


def _response_publish_targets(job: Path, state: dict[str, Any]) -> list[Path]:
    artifacts = _artifacts(job, state)
    if state["phase"] == "awaiting-sequence-review":
        return [
            artifacts / "production-request-v4.json",
            artifacts / "package",
            artifacts / "diagnostics",
        ]
    if state["phase"] == "awaiting-package-review":
        output = Path(state["intent"]["output_scope"].get("delivery_dir", artifacts / "sealed-delivery"))
        return [artifacts / "review-packet.json", artifacts / "delivery-request.json", output]
    return []


def _capture_publish_identities(targets: list[tuple[Path, bool]]) -> list[tuple[Path, bool, tuple[int, int] | None]]:
    captured = []
    for path, existed in targets:
        try:
            metadata = path.lstat()
            identity = (metadata.st_dev, metadata.st_ino)
        except FileNotFoundError:
            identity = None
        captured.append((path, existed, identity))
    return captured


def _remove_new_publish_targets(targets: list[tuple[Path, bool, tuple[int, int] | None]]) -> None:
    for path, existed, identity in reversed(targets):
        if existed:
            continue
        try:
            current = path.lstat()
        except FileNotFoundError:
            continue
        if identity is None or (current.st_dev, current.st_ino) != identity:
            continue
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)


def _job_paths(job: Path) -> set[Path]:
    if not job.exists():
        return set()
    return {job, *job.rglob("*")}


def _remove_new_job_paths(job: Path, before: set[Path]) -> None:
    for path in sorted(_job_paths(job) - before, key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def _paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve(strict=False)
    right = right.resolve(strict=False)
    return left == right or left in right.parents or right in left.parents


def _validate_path_isolation(job: Path, intent: dict[str, Any]) -> None:
    paths: list[Path] = []
    scope = intent.get("output_scope", {})
    for key in ("subject", "delivery_dir"):
        if key in scope:
            paths.append(Path(scope[key]))
    paths.extend(Path(item["path"]) for item in intent.get("identity", {}).get("sources", []))
    for path in paths:
        if _paths_overlap(job, path):
            raise ProductionError("PATH_OVERLAP", "job and input/output paths must not overlap")
    for index, left in enumerate(paths):
        for right in paths[index + 1:]:
            if _paths_overlap(left, right):
                raise ProductionError("PATH_OVERLAP", "input and output paths must not overlap")


def _advance_locked(job: Path, intent_value: dict[str, Any] | None, response_value: dict[str, Any] | None) -> dict[str, Any]:
    state_path = job / STATE
    if intent_value is not None:
        before_paths = _job_paths(job)
        intent = validate_intent(intent_value)
        _validate_path_isolation(job, intent)
        unchanged = False
        if state_path.exists():
            state = read_json(state_path)
            _validate_state(state)
            unchanged = state.get("intent_material_sha256") == _intent_material_digest(intent)
            if not unchanged and intent.get("base_revision") != state["revision"]:
                raise ProductionError("STALE_JOB_REVISION", "intent base_revision does not match the current job revision")
            _update_intent(job, state, intent)
        else:
            if intent.get("base_revision") is not None:
                raise ProductionError("STALE_JOB_REVISION", "initial intent base_revision must be null")
            if job.exists() and any(job.iterdir()):
                raise ProductionError(
                    "UNCOMMITTED_JOB_RESIDUE",
                    "a new job must not reuse uncommitted files; remove or relocate the residual job directory",
                )
            job.mkdir(parents=True, exist_ok=True)
            state = _new_state(intent)
        try:
            if intent["mode"] in {"diagnose", "review"}:
                _read_only_job(job, state)
            elif state["phase"] == "initializing":
                _prepare(job, state)
            if not unchanged:
                _save(job, state)
        except BaseException:
            _remove_new_job_paths(job, before_paths)
            raise
    else:
        if not state_path.exists():
            raise ProductionError("JOB_NOT_FOUND", "job state does not exist")
        state = read_json(state_path)
        _validate_state(state)
    if response_value is not None:
        before_paths = _job_paths(job)
        kind, payload = _response(response_value, state)
        raw_targets = [(path, path.exists() or path.is_symlink()) for path in _response_publish_targets(job, state)]
        captured_targets: list[tuple[Path, bool, tuple[int, int] | None]] = []
        try:
            _apply_response(job, state, kind, payload)
            captured_targets = _capture_publish_identities(raw_targets)
            if state["phase"] == "package-ready":
                _failure_point("seal")
            state["revision"] += 1
            _save(job, state)
        except BaseException:
            _remove_new_publish_targets(captured_targets)
            _remove_new_job_paths(job, before_paths)
            raise
    return {"ok": True, "result": {"job": str(job), "state": state}}


def advance_job(job: Path, intent_value: dict[str, Any] | None, response_value: dict[str, Any] | None) -> dict[str, Any]:
    if not job.is_absolute():
        raise ProductionError("INVALID_CONTRACT", "job path must be absolute")
    if job.is_symlink():
        raise ProductionError("INVALID_INPUT_FILE", "job path must not be a symlink")
    try:
        with LockedJob(job):
            return _advance_locked(job, intent_value, response_value)
    except ValueError as error:
        raise ProductionError("JOB_LOCK_INVALID", "job lock is not safe") from error


def verify_subject(subject: Path) -> dict[str, Any]:
    if subject.is_symlink():
        raise ProductionError("INVALID_INPUT_FILE", "subject must not be a symlink")
    before = tree_snapshot(subject)
    manifest = subject / "manifest.json" if subject.is_dir() else subject
    delivery = subject / "delivery.json" if subject.is_dir() else None
    if delivery is not None and delivery.is_file() and not manifest.is_file():
        adapter = Path(__file__).parents[1] / "spritesheet_delivery.py"
        completed = subprocess.run(
            [sys.executable, str(adapter), "verify", "--delivery", str(delivery)],
            check=False, capture_output=True, text=True,
        )
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise ProductionError("DELIVERY_ADAPTER_FAILED", "delivery verifier emitted invalid JSON", {"adapter": "delivery-verify"}) from error
        after = tree_snapshot(subject)
        if before != after:
            raise ProductionError("READ_ONLY_VIOLATION", "subject changed during delivery verification")
        if completed.returncode:
            raise ProductionError("DELIVERY_VERIFICATION_FAILED", "sealed delivery did not verify", {"report": report})
        return {"ok": True, "result": {"subject": str(subject), "state": report.get("status", "package-ready"), "verification": report, "snapshot": before}}
    if manifest.name != "manifest.json" or not manifest.is_file():
        raise ProductionError("UNSUPPORTED_SUBJECT", "subject must be a v4 package manifest or package directory")
    try:
        sha256_file(manifest)
    except (OSError, ValueError) as error:
        raise ProductionError("INVALID_INPUT_FILE", "manifest is not a safe bounded regular file") from error
    run_legacy("verify-package", "--manifest", str(manifest))
    after = tree_snapshot(subject)
    if before != after:
        raise ProductionError("READ_ONLY_VIOLATION", "subject changed during verification")
    return {
        "ok": True,
        "result": {
            "subject": str(subject), "manifest": str(manifest),
            "manifest_sha256": sha256_file(manifest), "subject_status": "pixel-package-verified",
            "delivery_state": None,
            "snapshot": before,
        },
    }
