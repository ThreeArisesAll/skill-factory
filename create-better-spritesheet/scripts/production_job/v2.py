"""Closed v2 production intent and complete motion-plan contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import MAX_ITEMS, MAX_TEXT, ProductionError

INTENT_SCHEMA = "spritesheet-production-intent/v2"
JOB_SCHEMA = "spritesheet-production-job/v3"
RESPONSE_SCHEMA = "spritesheet-production-response/v2"
SUPPORTED_PROFILE = "smooth-raster/v2"
IDENTITY_SCHEMA = "identity-bible/v2"
MOTION_PLAN_SCHEMA = "motion-plan/v2"

_ART_ARRAY_FIELDS = {
    "proportion_rules",
    "palette_rules",
    "material_rules",
    "lighting_and_shadow_rules",
    "recognition_constraints",
    "allowed_variations",
    "forbidden_drifts",
}
_POSITION_TEXT_FIELDS = {
    "id",
    "phase",
    "action_beat",
    "purpose",
    "pose",
    "orientation",
    "projection",
    "foreshortening",
    "depth_and_occlusion",
    "root_and_center_of_mass",
    "arc",
    "spacing",
    "transition_from_previous",
    "transition_to_next",
}
_POSITION_ARRAY_FIELDS = {
    "newly_visible_surfaces",
    "contacts",
    "equipment_state",
    "effect_state",
    "events",
}


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionError("INVALID_CONTRACT", f"{location} must be an object")
    return value


def _closed(value: dict[str, Any], expected: set[str], location: str) -> None:
    if set(value) != expected:
        raise ProductionError(
            "INVALID_CONTRACT",
            f"{location} contains unsupported or missing fields",
            {"missing": sorted(expected - set(value)), "unsupported": sorted(set(value) - expected)},
        )


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_TEXT:
        raise ProductionError("INVALID_CONTRACT", f"{location} must be a non-empty bounded string")
    return value


def _strings(value: Any, location: str, *, require_nonempty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > MAX_ITEMS
        or (require_nonempty and not value)
        or any(not isinstance(item, str) or not 1 <= len(item) <= MAX_TEXT for item in value)
    ):
        raise ProductionError("INVALID_CONTRACT", f"{location} must be a bounded string array")
    return value


def _validate_read_only(intent: dict[str, Any]) -> dict[str, Any]:
    allowed = {"schema_version", "base_revision", "mode", "output_scope", "runtime_scope"}
    if set(intent) - allowed:
        raise ProductionError("INVALID_CONTRACT", "read-only intent contains production fields")
    scope = _object(intent.get("output_scope"), "output_scope")
    _closed(scope, {"subject"}, "output_scope")
    subject = Path(_string(scope.get("subject"), "output_scope.subject"))
    if not subject.is_absolute():
        raise ProductionError("INVALID_CONTRACT", "output_scope.subject must be absolute")
    if intent.get("runtime_scope") is not None:
        raise ProductionError("INVALID_CONTRACT", "runtime_scope is currently limited to null")
    return intent


def _validate_art_contract(value: Any) -> dict[str, Any]:
    contract = _object(value, "identity.art_contract")
    _closed(contract, {"subject", "art_direction", *_ART_ARRAY_FIELDS, "equipment"}, "identity.art_contract")
    _string(contract.get("subject"), "identity.art_contract.subject")
    _string(contract.get("art_direction"), "identity.art_contract.art_direction")
    for field in _ART_ARRAY_FIELDS:
        _strings(
            contract.get(field),
            f"identity.art_contract.{field}",
            require_nonempty=field in {"recognition_constraints", "proportion_rules"},
        )
    equipment = contract.get("equipment")
    if not isinstance(equipment, list) or len(equipment) > MAX_ITEMS:
        raise ProductionError("INVALID_CONTRACT", "identity.art_contract.equipment must be an array")
    equipment_ids: set[str] = set()
    for index, raw in enumerate(equipment):
        item = _object(raw, f"identity.art_contract.equipment[{index}]")
        _closed(item, {"id", "side", "invariants"}, f"identity.art_contract.equipment[{index}]")
        identifier = _string(item.get("id"), f"identity.art_contract.equipment[{index}].id")
        if identifier in equipment_ids:
            raise ProductionError("INVALID_CONTRACT", "equipment IDs must be unique")
        equipment_ids.add(identifier)
        _string(item.get("side"), f"identity.art_contract.equipment[{index}].side")
        _strings(item.get("invariants"), f"identity.art_contract.equipment[{index}].invariants", require_nonempty=True)
    return contract


def _validate_position(value: Any, location: str) -> dict[str, Any]:
    position = _object(value, location)
    role = position.get("role")
    if role in {"keyframe", "in-between"}:
        expected = _POSITION_TEXT_FIELDS | _POSITION_ARRAY_FIELDS | {"role", "duration_ms"}
        _closed(position, expected, location)
        for field in _POSITION_TEXT_FIELDS:
            _string(position.get(field), f"{location}.{field}")
        for field in _POSITION_ARRAY_FIELDS:
            _strings(position.get(field), f"{location}.{field}")
    elif role == "alias":
        expected = {
            "id", "role", "alias_of", "alias_kind", "phase", "purpose",
            "duration_ms", "events", "transition_from_previous", "transition_to_next",
        }
        _closed(position, expected, location)
        for field in {"id", "alias_of", "alias_kind", "phase", "purpose", "transition_from_previous", "transition_to_next"}:
            _string(position.get(field), f"{location}.{field}")
        if position.get("alias_kind") not in {"hold", "closing"}:
            raise ProductionError("INVALID_CONTRACT", f"{location}.alias_kind is invalid")
        _strings(position.get("events"), f"{location}.events")
    else:
        raise ProductionError("INVALID_CONTRACT", f"{location}.role is invalid")
    if type(position.get("duration_ms")) is not int or not 1 <= position["duration_ms"] <= 60000:
        raise ProductionError("INVALID_CONTRACT", f"{location}.duration_ms must be between 1 and 60000")
    return position


def validate_intent(value: Any) -> dict[str, Any]:
    intent = _object(value, "intent")
    if intent.get("schema_version") != INTENT_SCHEMA:
        raise ProductionError("INVALID_CONTRACT", f"schema_version must be {INTENT_SCHEMA!r}")
    mode = intent.get("mode")
    if mode not in {"create", "rebuild", "diagnose", "review"}:
        raise ProductionError("INVALID_CONTRACT", "mode must be create, rebuild, diagnose, or review")
    base_revision = intent.get("base_revision")
    if base_revision is not None and (type(base_revision) is not int or base_revision < 1):
        raise ProductionError("INVALID_CONTRACT", "base_revision must be null or a positive integer")
    if mode in {"diagnose", "review"}:
        return _validate_read_only(intent)
    _closed(intent, {
        "schema_version", "base_revision", "mode", "identity", "clips", "target",
        "rendering_profile", "output_scope", "runtime_scope",
    }, "intent")

    identity = _object(intent.get("identity"), "identity")
    _closed(identity, {"sources", "art_contract"}, "identity")
    sources = identity.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_ITEMS:
        raise ProductionError("INVALID_CONTRACT", "identity.sources must be a non-empty bounded array")
    source_ids: set[str] = set()
    view_keys: set[tuple[str, str]] = set()
    for index, raw in enumerate(sources):
        source = _object(raw, f"identity.sources[{index}]")
        _closed(source, {"id", "path", "direction", "camera"}, f"identity.sources[{index}]")
        identifier = _string(source.get("id"), f"identity.sources[{index}].id")
        path = Path(_string(source.get("path"), f"identity.sources[{index}].path"))
        direction = _string(source.get("direction"), f"identity.sources[{index}].direction")
        camera = _string(source.get("camera"), f"identity.sources[{index}].camera")
        key = (direction, camera)
        if identifier in source_ids or key in view_keys or not path.is_absolute():
            raise ProductionError("INVALID_CONTRACT", "canonical views require unique IDs, unique direction-camera bindings, and absolute paths")
        source_ids.add(identifier)
        view_keys.add(key)
    _validate_art_contract(identity.get("art_contract"))

    clips = intent.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= MAX_ITEMS:
        raise ProductionError("INVALID_CONTRACT", "clips must be a non-empty bounded array")
    sources_by_id = {source["id"]: source for source in sources}
    clip_ids: set[str] = set()
    global_position_ids: set[str] = set()
    for clip_index, raw in enumerate(clips):
        clip = _object(raw, f"clips[{clip_index}]")
        _closed(clip, {
            "id", "canonical_view", "direction", "camera", "topology", "intent", "entry", "exit",
            "loop", "root_motion", "transition", "terminal_hold", "action_evidence", "positions",
        }, f"clips[{clip_index}]")
        identifier = _string(clip.get("id"), f"clips[{clip_index}].id")
        canonical_view = clip.get("canonical_view")
        if identifier in clip_ids or canonical_view not in sources_by_id:
            raise ProductionError("INVALID_CONTRACT", "clips require unique IDs and a declared canonical_view")
        clip_ids.add(identifier)
        for field in {"direction", "camera", "topology", "intent", "entry", "exit", "root_motion", "transition"}:
            _string(clip.get(field), f"clips[{clip_index}].{field}")
        source = sources_by_id[str(canonical_view)]
        if clip["direction"] != source["direction"] or clip["camera"] != source["camera"]:
            raise ProductionError(
                "CANONICAL_VIEW_MISMATCH",
                "clip direction and camera must match its canonical_view",
                {"clip": identifier, "canonical_view": canonical_view},
            )
        if not isinstance(clip.get("loop"), bool) or not isinstance(clip.get("terminal_hold"), bool):
            raise ProductionError("INVALID_CONTRACT", "clip loop and terminal_hold must be booleans")
        evidence = clip.get("action_evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_ITEMS:
            raise ProductionError("MATERIAL_INPUT_REQUIRED", f"clip {identifier!r} requires action evidence")
        evidence_ids: set[str] = set()
        for evidence_index, raw_evidence in enumerate(evidence):
            item = _object(raw_evidence, f"clips[{clip_index}].action_evidence[{evidence_index}]")
            _closed(item, {"evidence_id", "ref", "relationship"}, f"clips[{clip_index}].action_evidence[{evidence_index}]")
            evidence_id = _string(item.get("evidence_id"), "action_evidence.evidence_id")
            _string(item.get("ref"), "action_evidence.ref")
            if evidence_id in evidence_ids or item.get("relationship") not in {"supplied-reference", "written-intent"}:
                raise ProductionError("INVALID_CONTRACT", "action evidence IDs or relationships are invalid")
            evidence_ids.add(evidence_id)
        positions = clip.get("positions")
        if not isinstance(positions, list) or not 1 <= len(positions) <= MAX_ITEMS:
            raise ProductionError("INVALID_CONTRACT", f"clip {identifier!r}.positions must be non-empty")
        local_ids: set[str] = set()
        concrete_ids: set[str] = set()
        for position_index, raw_position in enumerate(positions):
            position = _validate_position(raw_position, f"clips[{clip_index}].positions[{position_index}]")
            position_id = position["id"]
            if position_id in local_ids or position_id in global_position_ids:
                raise ProductionError("INVALID_CONTRACT", "motion-plan position IDs must be globally unique")
            if position["role"] == "alias":
                if position["alias_of"] not in concrete_ids:
                    raise ProductionError("INVALID_CONTRACT", "an alias must reference an earlier concrete position in the same clip")
                if position["alias_kind"] == "closing" and (not clip["loop"] or position_index != len(positions) - 1):
                    raise ProductionError("INVALID_CONTRACT", "a closing alias must be the final position of a loop")
            else:
                concrete_ids.add(position_id)
            local_ids.add(position_id)
            global_position_ids.add(position_id)
        if not concrete_ids:
            raise ProductionError("INVALID_CONTRACT", "each clip requires at least one concrete position")

    target = _object(intent.get("target"), "target")
    _closed(target, {"frame_width", "frame_height", "animation_origin", "anchor", "safe_bounds", "columns"} if "columns" in target else {"frame_width", "frame_height", "animation_origin", "anchor", "safe_bounds"}, "target")
    for field in {"frame_width", "frame_height"}:
        if type(target.get(field)) is not int or not 1 <= target[field] <= 4096:
            raise ProductionError("INVALID_CONTRACT", f"target.{field} must be a positive integer")
    if min(target["frame_width"], target["frame_height"]) >= 512:
        raise ProductionError("INVALID_CONTRACT", "target shortest side must be smaller than 512")
    if "columns" in target and (type(target["columns"]) is not int or target["columns"] < 1):
        raise ProductionError("INVALID_CONTRACT", "target.columns must be a positive integer")
    for field in {"animation_origin", "anchor"}:
        point = target.get(field)
        if not isinstance(point, list) or len(point) != 2 or any(type(item) is not int for item in point):
            raise ProductionError("INVALID_CONTRACT", f"target.{field} must contain two integers")
    bounds = target.get("safe_bounds")
    if not isinstance(bounds, list) or len(bounds) != 4 or any(type(item) is not int for item in bounds):
        raise ProductionError("INVALID_CONTRACT", "target.safe_bounds must contain four integers")
    if not (0 <= bounds[0] < bounds[2] <= target["frame_width"] and 0 <= bounds[1] < bounds[3] <= target["frame_height"]):
        raise ProductionError("INVALID_CONTRACT", "target.safe_bounds must fit the target")

    profile = _object(intent.get("rendering_profile"), "rendering_profile")
    _closed(profile, {"id", "outline", "quality_thresholds"}, "rendering_profile")
    if profile.get("id") != SUPPORTED_PROFILE:
        raise ProductionError("UNSUPPORTED_CAPABILITY", "the requested rendering profile has no installed adapter", {"capability": profile.get("id")})
    outline = _object(profile.get("outline"), "rendering_profile.outline")
    _closed(outline, {"enabled", "target_width", "color"} if outline.get("enabled") else {"enabled", "target_width"}, "rendering_profile.outline")
    if not isinstance(outline.get("enabled"), bool):
        raise ProductionError("INVALID_CONTRACT", "rendering_profile.outline.enabled must be boolean")
    if outline["enabled"]:
        if type(outline.get("target_width")) is not int or outline["target_width"] < 1:
            raise ProductionError("INVALID_CONTRACT", "enabled outline target_width must be positive")
        color = outline.get("color")
        if not isinstance(color, list) or len(color) != 4 or any(type(item) is not int or not 0 <= item <= 255 for item in color) or color[3] != 255:
            raise ProductionError("INVALID_CONTRACT", "enabled outline color must be opaque RGBA bytes")
    elif outline.get("target_width") != "none":
        raise ProductionError("INVALID_CONTRACT", "disabled outline target_width must be 'none'")
    thresholds = _object(profile.get("quality_thresholds"), "rendering_profile.quality_thresholds")
    _closed(thresholds, {"transparent_rgb", "minimum_margin", "maximum_alpha_centroid_step"}, "rendering_profile.quality_thresholds")
    if thresholds.get("transparent_rgb") != "reject":
        raise ProductionError(
            "UNSUPPORTED_CAPABILITY",
            "smooth-raster/v2 requires transparent_rgb='reject'; normalization evidence is not installed",
        )
    for field in {"minimum_margin", "maximum_alpha_centroid_step"}:
        if type(thresholds.get(field)) is not int or thresholds[field] < 0:
            raise ProductionError("INVALID_CONTRACT", f"quality_thresholds.{field} must be a non-negative integer")
    output_scope = _object(intent.get("output_scope"), "output_scope")
    if set(output_scope) - {"delivery_dir"}:
        raise ProductionError("INVALID_CONTRACT", "output_scope contains unsupported fields")
    if "delivery_dir" in output_scope and not Path(_string(output_scope["delivery_dir"], "output_scope.delivery_dir")).is_absolute():
        raise ProductionError("INVALID_CONTRACT", "output_scope.delivery_dir must be absolute")
    if intent.get("runtime_scope") is not None:
        raise ProductionError("INVALID_CONTRACT", "runtime_scope is currently limited to null")
    return intent


def identity_content(intent: dict[str, Any], canonicals: dict[str, dict[str, Any]], sha256_file: Any) -> dict[str, Any]:
    contract = intent["identity"]["art_contract"]
    return {
        "subject": contract["subject"],
        "art_direction": contract["art_direction"],
        "canonical_views": [
            {
                "canonical_id": source["id"],
                "direction": source["direction"],
                "camera": source["camera"],
                "candidate_sha256": sha256_file(Path(canonicals[source["id"]]["path"])),
                "admission_proof_sha256": sha256_file(Path(canonicals[source["id"]]["proof_path"])),
            }
            for source in intent["identity"]["sources"]
        ],
        "proportion_rules": contract["proportion_rules"],
        "palette_rules": contract["palette_rules"],
        "material_rules": contract["material_rules"],
        "lighting_and_shadow_rules": contract["lighting_and_shadow_rules"],
        "recognition_constraints": contract["recognition_constraints"],
        "allowed_variations": contract["allowed_variations"],
        "forbidden_drifts": contract["forbidden_drifts"],
        "equipment": contract["equipment"],
    }


def motion_plan_content(intent: dict[str, Any], identity_bible_sha256: str) -> dict[str, Any]:
    return {
        "identity_bible_sha256": identity_bible_sha256,
        "clips": [
            {
                "id": clip["id"],
                "canonical_view": clip["canonical_view"],
                "direction": clip["direction"],
                "camera": clip["camera"],
                "topology": clip["topology"],
                "intent": clip["intent"],
                "entry": clip["entry"],
                "exit": clip["exit"],
                "loop": clip["loop"],
                "root_motion": clip["root_motion"],
                "transition": clip["transition"],
                "terminal_hold": clip["terminal_hold"],
                "action_evidence": clip["action_evidence"],
                "positions": [dict(position, index=index) for index, position in enumerate(clip["positions"])],
            }
            for clip in intent["clips"]
        ],
    }
