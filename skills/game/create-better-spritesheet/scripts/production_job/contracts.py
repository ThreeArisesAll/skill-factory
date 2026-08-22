"""High-level intent validation and legacy topology projection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from spritesheet_core import protocol as core_protocol

INTENT_SCHEMA = "spritesheet-production-intent/v1"
JOB_SCHEMA = "spritesheet-production-job/v2"
PIXEL_PROTOCOL_ID = core_protocol.PIXEL_PROTOCOL_ID
RESPONSE_SCHEMA = "spritesheet-production-response/v1"
SUPPORTED_PROFILE = "smooth-raster/v1"
MAX_ITEMS = 256
MAX_TEXT = 4096


class ProductionError(Exception):
    """A stable typed production failure."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionError("INVALID_CONTRACT", f"{location} must be an object")
    return value


def _closed(value: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ProductionError("INVALID_CONTRACT", f"{location} contains unsupported fields", {"fields": unknown})


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT:
        raise ProductionError("INVALID_CONTRACT", f"{location} must be a non-empty string")
    return value


def validate_intent(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("schema_version") == "spritesheet-production-intent/v2":
        from .v2 import validate_intent as validate_v2_intent

        return validate_v2_intent(value)
    return _validate_v1_intent(value)


def _validate_v1_intent(value: Any) -> dict[str, Any]:
    intent = _object(value, "intent")
    _closed(intent, {
        "schema_version", "mode", "identity", "clips", "target",
        "rendering_profile", "output_scope", "runtime_scope", "base_revision",
    }, "intent")
    if intent.get("schema_version") != INTENT_SCHEMA:
        raise ProductionError("INVALID_CONTRACT", f"schema_version must be {INTENT_SCHEMA!r}")
    mode = intent.get("mode", "create")
    base_revision = intent.get("base_revision")
    if base_revision is not None and (type(base_revision) is not int or base_revision < 1):
        raise ProductionError("INVALID_CONTRACT", "base_revision must be null or a positive integer")
    if mode not in {"create", "rebuild", "diagnose", "review"}:
        raise ProductionError("INVALID_CONTRACT", "mode must be create, rebuild, diagnose, or review")
    output_scope = _object(intent.get("output_scope"), "output_scope")
    _closed(output_scope, {"subject"} if mode in {"diagnose", "review"} else {"delivery_dir"}, "output_scope")
    if mode not in {"diagnose", "review"} and "delivery_dir" in output_scope and not Path(str(output_scope["delivery_dir"])).is_absolute():
        raise ProductionError("INVALID_CONTRACT", "output_scope.delivery_dir must be absolute")
    if mode in {"diagnose", "review"}:
        subject = Path(_string(output_scope.get("subject"), "output_scope.subject"))
        if not subject.is_absolute():
            raise ProductionError("INVALID_CONTRACT", "output_scope.subject must be absolute")
        if intent.get("identity") is not None or intent.get("clips") is not None or intent.get("target") is not None or intent.get("rendering_profile") is not None:
            raise ProductionError("INVALID_CONTRACT", "read-only intent accepts only mode, output_scope, and optional runtime_scope")
        if intent.get("runtime_scope") is not None:
            raise ProductionError("INVALID_CONTRACT", "runtime_scope is currently limited to null")
        return intent
    identity = _object(intent.get("identity"), "identity")
    _closed(identity, {"sources", "declarations"}, "identity")
    sources = identity.get("sources")
    if not isinstance(sources, list) or not sources or len(sources) > MAX_ITEMS:
        raise ProductionError("INVALID_CONTRACT", "identity.sources must be a non-empty array")
    source_ids: set[str] = set()
    for index, raw in enumerate(sources):
        source = _object(raw, f"identity.sources[{index}]")
        _closed(source, {"id", "path"}, f"identity.sources[{index}]")
        source_id = _string(source.get("id"), f"identity.sources[{index}].id")
        source_path = Path(_string(source.get("path"), f"identity.sources[{index}].path"))
        if source_id in source_ids or not source_path.is_absolute():
            raise ProductionError("INVALID_CONTRACT", "identity sources require unique IDs and absolute paths")
        source_ids.add(source_id)
    declarations = _object(identity.get("declarations"), "identity.declarations")
    _closed(declarations, {
        "subject", "art_direction", "camera", "direction", "recognition_constraints",
        "allowed_variations", "forbidden_drifts",
    }, "identity.declarations")
    for field in ("subject", "art_direction", "camera", "direction"):
        _string(declarations.get(field), f"identity.declarations.{field}")
    constraints = declarations.get("recognition_constraints")
    if not isinstance(constraints, list) or len(constraints) > MAX_ITEMS or any(not isinstance(item, str) or not item or len(item) > MAX_TEXT for item in constraints):
        raise ProductionError("INVALID_CONTRACT", "identity.declarations.recognition_constraints must be an array of strings")
    for field in ("allowed_variations", "forbidden_drifts"):
        values = declarations.get(field, [])
        if not isinstance(values, list) or len(values) > MAX_ITEMS or any(not isinstance(item, str) or not item or len(item) > MAX_TEXT for item in values):
            raise ProductionError("INVALID_CONTRACT", f"identity.declarations.{field} must be an array of strings")
    clips = intent.get("clips")
    if not isinstance(clips, list) or not clips or len(clips) > MAX_ITEMS:
        raise ProductionError("INVALID_CONTRACT", "clips must be a non-empty array")
    clip_ids: set[str] = set()
    for clip_index, raw in enumerate(clips):
        clip = _object(raw, f"clips[{clip_index}]")
        _closed(clip, {
            "id", "identity_source", "direction", "camera", "loop", "root_motion",
            "transition", "terminal_hold", "durations_ms", "events", "positions",
            "intent", "entry", "exit", "action_evidence",
        }, f"clips[{clip_index}]")
        clip_id = _string(clip.get("id"), f"clips[{clip_index}].id")
        if clip_id in clip_ids or clip.get("identity_source") not in source_ids:
            raise ProductionError("INVALID_CONTRACT", "clips require unique IDs and a declared identity_source")
        clip_ids.add(clip_id)
        positions = clip.get("positions")
        if not isinstance(positions, list) or not positions or len(positions) > MAX_ITEMS:
            raise ProductionError("INVALID_CONTRACT", f"clip {clip_id!r} positions must be a non-empty array")
        position_ids: set[str] = set()
        for position_index, raw_position in enumerate(positions):
            position = _object(raw_position, f"clip {clip_id!r}.positions[{position_index}]")
            _closed(position, {
                "id", "role", "phase", "action_beat", "purpose", "pose", "orientation",
                "projection", "depth_and_occlusion", "root_and_alpha_centroid_intent", "contacts",
                "transition_from_previous", "transition_to_next", "events",
            }, f"clip {clip_id!r}.positions[{position_index}]")
            position_id = _string(position.get("id"), "position.id")
            if position_id in position_ids or position.get("role") != "keyframe":
                raise ProductionError("INVALID_CONTRACT", f"clip {clip_id!r} position IDs and roles are invalid")
            position_ids.add(position_id)
            _string(position.get("phase"), "position.phase")
            for field in ("contacts", "events"):
                if field in position and (not isinstance(position[field], list) or len(position[field]) > MAX_ITEMS or any(not isinstance(item, str) or not item or len(item) > MAX_TEXT for item in position[field])):
                    raise ProductionError("INVALID_CONTRACT", f"position.{field} must be a bounded array of strings")
            for field in ("action_beat", "purpose", "pose", "orientation", "projection", "depth_and_occlusion", "root_and_alpha_centroid_intent", "transition_from_previous", "transition_to_next"):
                if field in position:
                    _string(position[field], f"position.{field}")
        durations = clip.get("durations_ms")
        if not isinstance(durations, list) or len(durations) != len(positions) or any(type(item) is not int or item < 1 for item in durations):
            raise ProductionError("INVALID_CONTRACT", f"clip {clip_id!r}.durations_ms must match positions")
        for field in ("direction", "camera", "root_motion", "transition"):
            _string(clip.get(field), f"clip {clip_id!r}.{field}")
        if not isinstance(clip.get("loop"), bool) or not isinstance(clip.get("terminal_hold"), bool):
            raise ProductionError("INVALID_CONTRACT", f"clip {clip_id!r} loop and terminal_hold must be boolean")
        if not isinstance(clip.get("events"), list) or len(clip["events"]) > MAX_ITEMS:
            raise ProductionError("INVALID_CONTRACT", f"clip {clip_id!r}.events must be an array")
        for event_index, raw_event in enumerate(clip["events"]):
            event = _object(raw_event, f"clip {clip_id!r}.events[{event_index}]")
            _closed(event, {"name", "position"}, f"clip {clip_id!r}.events[{event_index}]")
            _string(event.get("name"), "event.name")
            if type(event.get("position")) is not int or not 0 <= event["position"] < len(positions):
                raise ProductionError("INVALID_CONTRACT", "event.position is out of range")
        action_evidence = clip.get("action_evidence", [])
        if not isinstance(action_evidence, list) or not action_evidence or len(action_evidence) > MAX_ITEMS:
            raise ProductionError("MATERIAL_INPUT_REQUIRED", f"clip {clip_id!r}.action_evidence must declare a supplied reference or written-intent authority")
        for evidence_index, raw_evidence in enumerate(action_evidence):
            evidence = _object(raw_evidence, f"clip.action_evidence[{evidence_index}]")
            _closed(evidence, {"evidence_id", "ref", "relationship"}, f"clip.action_evidence[{evidence_index}]")
            _string(evidence.get("evidence_id"), "action_evidence.evidence_id")
            _string(evidence.get("ref"), "action_evidence.ref")
            if evidence.get("relationship") not in {"supplied-reference", "written-intent"}:
                raise ProductionError("INVALID_CONTRACT", "action_evidence.relationship is invalid")
    target = _object(intent.get("target"), "target")
    _closed(target, {"frame_width", "frame_height", "animation_origin", "anchor", "safe_bounds", "columns"}, "target")
    for field in ("frame_width", "frame_height"):
        if type(target.get(field)) is not int or not 1 <= target[field] <= 4096:
            raise ProductionError("INVALID_CONTRACT", f"target.{field} must be a positive integer")
    if "columns" in target and (type(target["columns"]) is not int or target["columns"] < 1):
        raise ProductionError("INVALID_CONTRACT", "target.columns must be a positive integer")
    for field in ("animation_origin", "anchor"):
        point = target.get(field)
        if not isinstance(point, list) or len(point) != 2 or any(type(item) is not int for item in point):
            raise ProductionError("INVALID_CONTRACT", f"target.{field} must contain two integers")
    bounds = target.get("safe_bounds")
    if not isinstance(bounds, list) or len(bounds) != 4 or any(type(item) is not int for item in bounds):
        raise ProductionError("INVALID_CONTRACT", "target.safe_bounds must contain four integers")
    if not (0 <= bounds[0] < bounds[2] <= target["frame_width"] and 0 <= bounds[1] < bounds[3] <= target["frame_height"]):
        raise ProductionError("INVALID_CONTRACT", "target.safe_bounds must fit the target")
    profile = _object(intent.get("rendering_profile"), "rendering_profile")
    _closed(profile, {"id", "outline"}, "rendering_profile")
    profile_id = _string(profile.get("id"), "rendering_profile.id")
    if profile_id != SUPPORTED_PROFILE:
        raise ProductionError("UNSUPPORTED_CAPABILITY", f"rendering profile {profile_id!r} has no installed render adapter", {"capability": profile_id})
    outline = _object(profile.get("outline"), "rendering_profile.outline")
    _closed(outline, {"enabled", "target_width", "color"} if outline.get("enabled") else {"enabled", "target_width"}, "rendering_profile.outline")
    if not isinstance(outline.get("enabled"), bool):
        raise ProductionError("INVALID_CONTRACT", "rendering_profile.outline.enabled must be boolean")
    if outline["enabled"]:
        if type(outline.get("target_width")) is not int or outline["target_width"] < 1:
            raise ProductionError("INVALID_CONTRACT", "enabled outline target_width must be positive")
        color = outline.get("color")
        if not isinstance(color, list) or len(color) != 4 or any(type(item) is not int or not 0 <= item <= 255 for item in color):
            raise ProductionError("INVALID_CONTRACT", "outline color must contain four byte values")
        if color[3] != 255:
            raise ProductionError("INVALID_CONTRACT", "outline color alpha must be 255")
    elif outline.get("target_width") != "none":
        raise ProductionError("INVALID_CONTRACT", "disabled outline target_width must be 'none'")
    if intent.get("runtime_scope") is not None:
        raise ProductionError("INVALID_CONTRACT", "runtime_scope is currently limited to null")
    return intent


def validate_legacy_topology(intent: dict[str, Any]) -> None:
    unsupported: list[dict[str, Any]] = []
    for clip in intent["clips"]:
        key_count = sum(position["role"] == "keyframe" for position in clip["positions"])
        between_count = sum(position["role"] == "in-between" for position in clip["positions"])
        if key_count < 2 or between_count < 2:
            unsupported.append({"clip": clip["id"], "keyframes": key_count, "in_betweens": between_count})
    if unsupported:
        raise ProductionError(
            "LEGACY_TOPOLOGY_UNSUPPORTED",
            "the installed v4 adapter cannot encode this approved action topology",
            {"clips": unsupported},
        )
