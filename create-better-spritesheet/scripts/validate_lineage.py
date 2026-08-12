#!/usr/bin/env python3
"""Validate a versioned spritesheet lineage evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import Image

SCHEMA_VERSION = "spritesheet-lineage/v1"
IMAGE_TYPES = {
    "high-resolution-pre-master",
    "canonical-master",
    "high-resolution-keyframe",
    "high-resolution-in-between",
    "target-frame",
    "spritesheet",
}
RELATION_TYPES = {
    "canonical-lock",
    "canonical-reference",
    "adjacent-keyframe-reference",
}
REVIEW_STAGE_BY_TYPE = {
    "canonical-master": "canonical-lock",
    "high-resolution-keyframe": "keyframe-approval",
    "high-resolution-in-between": "in-between-approval",
}


@dataclass(frozen=True)
class Finding:
    level: str
    passed: bool | None
    location: str
    detail: str


class Validator:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.base_dir = manifest_path.parent
        self.findings: list[Finding] = []
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.images: dict[str, Image.Image] = {}
        self.relations: list[dict[str, Any]] = []

    def machine(self, passed: bool, location: str, detail: str) -> None:
        self.findings.append(Finding("MACHINE-VERIFIED", passed, location, detail))

    def declared(self, location: str, detail: str) -> None:
        self.findings.append(Finding("DECLARED", None, location, detail))

    def reviewed(self, location: str, detail: str) -> None:
        self.findings.append(Finding("REVIEWED", None, location, detail))

    def validate(self, data: Any) -> None:
        if not isinstance(data, dict):
            self.machine(False, "$", "manifest must be a JSON object")
            return

        version = data.get("schema_version")
        self.machine(
            version == SCHEMA_VERSION,
            "schema_version",
            f"actual={version!r}, expected={SCHEMA_VERSION!r}",
        )
        contract = self._object(data.get("contract"), "contract")
        artifacts = self._list(data.get("artifacts"), "artifacts")
        relations = self._list(data.get("relations"), "relations")
        clips = self._list(data.get("clips"), "clips")
        reviews = self._list(data.get("reviews"), "reviews")
        transforms = self._list(data.get("transforms"), "transforms")
        assembly = self._object(data.get("assembly"), "assembly")

        contract_values = self._validate_contract(contract)
        self._validate_artifacts(artifacts, contract_values)
        self._validate_relations(relations, contract)
        frames = self._validate_clips(clips, contract_values)
        review_orders = self._validate_reviews(reviews)
        self._validate_review_order(review_orders, frames)
        self._validate_transforms(transforms, frames, review_orders)
        self._validate_assembly(assembly, frames, contract_values)
        self._validate_artifact_graph(frames, transforms, assembly)

    def _object(self, value: Any, location: str) -> dict[str, Any]:
        valid = isinstance(value, dict)
        self.machine(valid, location, "is an object" if valid else "must be an object")
        return value if valid else {}

    def _list(self, value: Any, location: str) -> list[Any]:
        valid = isinstance(value, list)
        self.machine(valid, location, "is an array" if valid else "must be an array")
        return value if valid else []

    def _positive_int(self, value: Any, location: str) -> int | None:
        valid = isinstance(value, int) and not isinstance(value, bool) and value > 0
        self.machine(valid, location, f"value={value!r}; must be a positive integer")
        return value if valid else None

    def _validate_contract(self, contract: dict[str, Any]) -> dict[str, int | None]:
        values = {
            name: self._positive_int(contract.get(name), f"contract.{name}")
            for name in ("frame_width", "frame_height", "frame_count", "canonical_short_side")
        }
        self.machine(
            values["canonical_short_side"] == 512,
            "contract.canonical_short_side",
            f"value={values['canonical_short_side']!r}, required=512",
        )
        outline = contract.get("outline")
        valid_outline = isinstance(outline, dict)
        self.machine(valid_outline, "contract.outline", "must be an object with enabled and target_width")
        if valid_outline:
            enabled = outline.get("enabled")
            target_width = outline.get("target_width")
            self.machine(isinstance(enabled, bool), "contract.outline.enabled", f"value={enabled!r}; must be boolean")
            width_valid = (
                isinstance(target_width, int)
                and not isinstance(target_width, bool)
                and target_width > 0
                if enabled is True
                else target_width == "none"
            )
            self.machine(
                width_valid,
                "contract.outline.target_width",
                f"value={target_width!r}; enabled requires a positive integer, disabled requires 'none'",
            )
            self.declared(
                "contract.outline",
                f"manifest declares outline enabled={enabled!r}, target_width={target_width!r}; application before canonical lock is historical",
            )
        return values

    def _validate_artifacts(self, entries: list[Any], contract: dict[str, int | None]) -> None:
        frame_width = contract.get("frame_width")
        frame_height = contract.get("frame_height")
        expected_high_resolution_size: tuple[int, int] | None = None
        if frame_width is not None and frame_height is not None:
            short_side = min(frame_width, frame_height)
            expected_high_resolution_size = (
                round(Fraction(frame_width * 512, short_side)),
                round(Fraction(frame_height * 512, short_side)),
            )
        seen: set[str] = set()
        for index, raw in enumerate(entries):
            location = f"artifacts[{index}]"
            if not isinstance(raw, dict):
                self.machine(False, location, "must be an object")
                continue
            artifact_id = raw.get("id")
            valid_id = isinstance(artifact_id, str) and bool(artifact_id)
            self.machine(valid_id, f"{location}.id", f"value={artifact_id!r}; must be a non-empty string")
            if not valid_id:
                continue
            unique = artifact_id not in seen
            self.machine(unique, f"{location}.id", f"id={artifact_id!r} is unique")
            if not unique:
                continue
            seen.add(artifact_id)
            self.artifacts[artifact_id] = raw

            artifact_type = raw.get("type")
            valid_type = isinstance(artifact_type, str) and artifact_type in IMAGE_TYPES
            self.machine(valid_type, f"{location}.type", f"value={artifact_type!r}; expected one of {sorted(IMAGE_TYPES)}")
            path_value = raw.get("path")
            valid_path = isinstance(path_value, str) and bool(path_value)
            self.machine(valid_path, f"{location}.path", f"value={path_value!r}; must be a non-empty string")
            expected_hash = raw.get("sha256")
            valid_hash = (
                isinstance(expected_hash, str)
                and len(expected_hash) == 64
                and all(character in "0123456789abcdef" for character in expected_hash)
            )
            self.machine(valid_hash, f"{location}.sha256", "must be 64 lowercase hexadecimal characters")
            declared_width = self._positive_int(raw.get("width"), f"{location}.width")
            declared_height = self._positive_int(raw.get("height"), f"{location}.height")
            self.machine(raw.get("mode") == "RGBA", f"{location}.mode", f"value={raw.get('mode')!r}, required='RGBA'")
            if not valid_path:
                continue
            path = (self.base_dir / path_value).resolve()
            exists = path.is_file()
            self.machine(exists, f"{location}.path", f"resolved={path}; file exists={exists}")
            if not exists:
                continue
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.machine(
                valid_hash and actual_hash == expected_hash,
                f"{location}.sha256",
                f"actual={actual_hash}, declared={expected_hash!r}",
            )
            try:
                with Image.open(path) as opened:
                    opened.load()
                    image = opened.copy()
            except (OSError, ValueError) as error:
                self.machine(False, f"{location}.image", f"cannot decode image: {error}")
                continue
            self.images[artifact_id] = image
            self.machine(
                declared_width == image.width and declared_height == image.height,
                f"{location}.dimensions",
                f"actual={image.width}x{image.height}, declared={declared_width}x{declared_height}",
            )
            self.machine(image.mode == "RGBA", f"{location}.image-mode", f"actual={image.mode}, required=RGBA")
            if valid_type and artifact_type in {
                "high-resolution-pre-master",
                "canonical-master",
                "high-resolution-keyframe",
                "high-resolution-in-between",
            }:
                self.machine(
                    expected_high_resolution_size is not None and image.size == expected_high_resolution_size,
                    f"{location}.high-resolution-canvas",
                    f"actual={image.size}, expected={expected_high_resolution_size}",
                )
            elif artifact_type == "target-frame":
                expected_target_size = (
                    (frame_width, frame_height)
                    if frame_width is not None and frame_height is not None
                    else None
                )
                self.machine(
                    expected_target_size is not None and image.size == expected_target_size,
                    f"{location}.target-frame-size",
                    f"actual={image.size}, expected={expected_target_size}",
                )

        masters = [item for item in self.artifacts.values() if item.get("type") == "canonical-master"]
        self.machine(bool(masters), "artifacts", f"canonical-master count={len(masters)}, required at least 1")

    def _known_reference(self, value: Any, location: str) -> bool:
        valid = isinstance(value, str) and value in self.artifacts
        self.machine(valid, location, f"artifact reference={value!r}; known={valid}")
        return valid

    def _pixel_fingerprint(self, artifact_id: Any) -> str | None:
        if not isinstance(artifact_id, str) or artifact_id not in self.images:
            return None
        image = self.images[artifact_id]
        digest = hashlib.sha256()
        digest.update(image.mode.encode("ascii"))
        digest.update(f"{image.width}x{image.height}".encode("ascii"))
        digest.update(image.tobytes())
        return digest.hexdigest()

    def _validate_relations(self, entries: list[Any], contract: dict[str, Any]) -> None:
        seen: set[str] = set()
        for index, raw in enumerate(entries):
            location = f"relations[{index}]"
            if not isinstance(raw, dict):
                self.machine(False, location, "must be an object")
                continue
            self.relations.append(raw)
            relation_id = raw.get("id")
            valid_id = isinstance(relation_id, str) and bool(relation_id) and relation_id not in seen
            self.machine(valid_id, f"{location}.id", f"value={relation_id!r}; must be a unique non-empty string")
            if isinstance(relation_id, str):
                seen.add(relation_id)
            relation_type = raw.get("type")
            valid_relation_type = isinstance(relation_type, str) and relation_type in RELATION_TYPES
            self.machine(
                valid_relation_type,
                f"{location}.type",
                f"value={relation_type!r}; expected one of {sorted(RELATION_TYPES)}",
            )
            sources = raw.get("sources")
            if not isinstance(sources, list) or not sources:
                self.machine(False, f"{location}.sources", "must be a non-empty array")
            else:
                for source_index, source in enumerate(sources):
                    self._known_reference(source, f"{location}.sources[{source_index}]")
            target = raw.get("target")
            self._known_reference(target, f"{location}.target")
            source_values = sources if isinstance(sources, list) else []
            source_types = [
                self.artifacts[source].get("type")
                for source in source_values
                if isinstance(source, str) and source in self.artifacts
            ]
            target_type = self.artifacts.get(target, {}).get("type") if isinstance(target, str) else None
            if relation_type == "canonical-lock":
                valid_endpoints = (
                    isinstance(sources, list)
                    and len(sources) == 1
                    and source_types == ["high-resolution-pre-master"]
                    and target_type == "canonical-master"
                )
            elif relation_type == "canonical-reference":
                valid_endpoints = (
                    isinstance(sources, list)
                    and len(sources) == 1
                    and source_types == ["canonical-master"]
                    and target_type == "high-resolution-keyframe"
                )
            elif relation_type == "adjacent-keyframe-reference":
                valid_endpoints = (
                    isinstance(sources, list)
                    and len(sources) == 2
                    and all(isinstance(source, str) for source in sources)
                    and len(set(sources)) == 2
                    and source_types == ["high-resolution-keyframe", "high-resolution-keyframe"]
                    and target_type == "high-resolution-in-between"
                )
            else:
                valid_endpoints = False
            self.machine(
                valid_endpoints,
                f"{location}.endpoints",
                f"type={relation_type!r}, source types={source_types}, target type={target_type!r}",
            )
            self.declared(
                location,
                f"manifest declares relation type={relation_type!r}; the creative derivation history is not observable from files",
            )

        outline = contract.get("outline") if isinstance(contract.get("outline"), dict) else {}
        masters = [artifact_id for artifact_id, artifact in self.artifacts.items() if artifact.get("type") == "canonical-master"]
        for master_id in masters:
            locks = [
                relation
                for relation in self.relations
                if relation.get("type") == "canonical-lock" and relation.get("target") == master_id
            ]
            valid_lock = len(locks) == 1
            if valid_lock:
                sources = locks[0].get("sources")
                valid_lock = (
                    isinstance(sources, list)
                    and len(sources) == 1
                    and isinstance(sources[0], str)
                    and sources[0] in self.artifacts
                    and self.artifacts[sources[0]].get("type") == "high-resolution-pre-master"
                    and locks[0].get("outline_enabled") == outline.get("enabled")
                    and locks[0].get("outline_target_width") == outline.get("target_width")
                )
            self.machine(
                valid_lock,
                f"relations[canonical-lock->{master_id}]",
                "requires exactly one high-resolution pre-master source and outline fields matching contract.outline",
            )
            if valid_lock and outline.get("enabled") is False:
                source_id = locks[0]["sources"][0]
                source_image = self.images.get(source_id)
                master_image = self.images.get(master_id)
                identical = (
                    source_image is not None
                    and master_image is not None
                    and source_image.mode == master_image.mode
                    and source_image.size == master_image.size
                    and source_image.tobytes() == master_image.tobytes()
                )
                self.machine(
                    identical,
                    f"relations[canonical-lock->{master_id}].disabled-outline-pixels",
                    "disabled outline requires the canonical master to be pixel-identical to its pre-master",
                )

    def _validate_clips(
        self,
        entries: list[Any],
        contract: dict[str, int | None],
    ) -> list[dict[str, Any]]:
        all_frames: list[dict[str, Any]] = []
        clip_ids: set[str] = set()
        for clip_index, raw in enumerate(entries):
            location = f"clips[{clip_index}]"
            if not isinstance(raw, dict):
                self.machine(False, location, "must be an object")
                continue
            clip_id = raw.get("id")
            valid_id = isinstance(clip_id, str) and bool(clip_id) and clip_id not in clip_ids
            self.machine(valid_id, f"{location}.id", f"value={clip_id!r}; must be a unique non-empty string")
            if isinstance(clip_id, str):
                clip_ids.add(clip_id)
            normalized_clip_id = clip_id if valid_id else f"__invalid_clip_{clip_index}"
            loop = raw.get("loop")
            self.machine(isinstance(loop, bool), f"{location}.loop", f"value={loop!r}; must be boolean")
            repeated_closing_target = raw.get("repeated_closing_target")
            self.machine(
                isinstance(repeated_closing_target, bool),
                f"{location}.repeated_closing_target",
                f"value={repeated_closing_target!r}; must be boolean",
            )
            self.machine(
                repeated_closing_target is not True or loop is True,
                f"{location}.repeated_closing_target",
                "a repeated closing target is valid only for a loop clip",
            )
            raw_frames = raw.get("frames")
            if not isinstance(raw_frames, list):
                self.machine(False, f"{location}.frames", "must be an array")
                continue
            frames: list[dict[str, Any]] = []
            for frame_position, frame in enumerate(raw_frames):
                frame_location = f"{location}.frames[{frame_position}]"
                if not isinstance(frame, dict):
                    self.machine(False, frame_location, "must be an object")
                    continue
                frame_index = frame.get("index")
                valid_index = isinstance(frame_index, int) and not isinstance(frame_index, bool) and frame_index >= 0
                self.machine(valid_index, f"{frame_location}.index", f"value={frame_index!r}; must be a non-negative integer")
                role = frame.get("role")
                valid_role = isinstance(role, str) and role in {"keyframe", "in-between"}
                self.machine(valid_role, f"{frame_location}.role", f"value={role!r}")
                high_resolution = frame.get("high_resolution")
                target = frame.get("target")
                high_known = self._known_reference(high_resolution, f"{frame_location}.high_resolution")
                target_known = self._known_reference(target, f"{frame_location}.target")
                if high_known:
                    expected_type = "high-resolution-keyframe" if role == "keyframe" else "high-resolution-in-between"
                    actual_type = self.artifacts[high_resolution].get("type")
                    self.machine(
                        actual_type == expected_type,
                        f"{frame_location}.high_resolution",
                        f"artifact type={actual_type!r}, expected={expected_type!r}",
                    )
                if target_known:
                    actual_type = self.artifacts[target].get("type")
                    self.machine(
                        actual_type == "target-frame",
                        f"{frame_location}.target",
                        f"artifact type={actual_type!r}, expected='target-frame'",
                    )
                if valid_index:
                    frames.append(frame)
                    all_frames.append({**frame, "_clip_id": normalized_clip_id})

            indices = [frame["index"] for frame in frames]
            self.machine(
                len(indices) == len(set(indices)) and indices == sorted(indices),
                f"{location}.frames",
                f"indices={indices}; must be unique and ascending",
            )
            keyframes = [frame for frame in frames if frame.get("role") == "keyframe"]
            in_betweens = [frame for frame in frames if frame.get("role") == "in-between"]
            self.machine(len(keyframes) >= 2, location, f"keyframes={len(keyframes)}, required at least 2")
            self.machine(len(in_betweens) >= 2, location, f"in-betweens={len(in_betweens)}, required at least 2")
            keyframe_artifacts = [frame.get("high_resolution") for frame in keyframes]
            in_between_artifacts = [frame.get("high_resolution") for frame in in_betweens]
            self.machine(
                all(isinstance(artifact_id, str) for artifact_id in keyframe_artifacts)
                and len(keyframe_artifacts) == len(set(keyframe_artifacts)),
                f"{location}.keyframes",
                "every keyframe index must use a distinct high-resolution artifact",
            )
            self.machine(
                all(isinstance(artifact_id, str) for artifact_id in in_between_artifacts)
                and len(in_between_artifacts) == len(set(in_between_artifacts)),
                f"{location}.in-betweens",
                "every in-between index must use a distinct high-resolution artifact",
            )
            keyframe_fingerprints = {
                fingerprint
                for artifact_id in keyframe_artifacts
                if (fingerprint := self._pixel_fingerprint(artifact_id)) is not None
            }
            in_between_fingerprints = {
                fingerprint
                for artifact_id in in_between_artifacts
                if (fingerprint := self._pixel_fingerprint(artifact_id)) is not None
            }
            self.machine(
                len(keyframe_fingerprints) == len(keyframe_artifacts),
                f"{location}.keyframe-pixels",
                f"distinct decoded high-resolution keyframe images={len(keyframe_fingerprints)}, "
                f"keyframe records={len(keyframe_artifacts)}; every keyframe image must be distinct",
            )
            self.machine(
                len(in_between_fingerprints) == len(in_between_artifacts),
                f"{location}.in-between-pixels",
                f"distinct decoded high-resolution in-between images={len(in_between_fingerprints)}, "
                f"in-between records={len(in_between_artifacts)}; every in-between image must be distinct",
            )
            target_fingerprints = [
                self._pixel_fingerprint(frame.get("target")) for frame in frames
            ]
            duplicate_target_pairs = [
                (first_index, second_index)
                for first_index, first in enumerate(target_fingerprints)
                if first is not None
                for second_index, second in enumerate(target_fingerprints[first_index + 1 :], start=first_index + 1)
                if first == second
            ]
            expected_duplicate_pairs = (
                [(0, len(frames) - 1)]
                if repeated_closing_target is True and len(frames) >= 2
                else []
            )
            self.machine(
                duplicate_target_pairs == expected_duplicate_pairs,
                f"{location}.target-pixels",
                f"duplicate target frame positions={duplicate_target_pairs}, expected={expected_duplicate_pairs}",
            )
            canonical_sources: list[str] = []
            for frame in keyframes:
                high_resolution = frame.get("high_resolution")
                canonical_relations = [
                    relation
                    for relation in self.relations
                    if relation.get("type") == "canonical-reference"
                    and relation.get("target") == high_resolution
                    and isinstance(relation.get("sources"), list)
                    and len(relation["sources"]) == 1
                    and isinstance(relation["sources"][0], str)
                    and relation["sources"][0] in self.artifacts
                    and self.artifacts[relation["sources"][0]].get("type") == "canonical-master"
                ]
                self.machine(
                    len(canonical_relations) == 1,
                    f"{location}.frame[index={frame['index']}].canonical-reference",
                    f"high-resolution keyframe={high_resolution!r} has {len(canonical_relations)} canonical-master declarations; required exactly 1",
                )
                if len(canonical_relations) == 1:
                    canonical_sources.append(canonical_relations[0]["sources"][0])
            self.machine(
                len(canonical_sources) == len(keyframes) and len(set(canonical_sources)) == 1,
                f"{location}.canonical-master",
                f"keyframe canonical masters={canonical_sources}; every keyframe in a clip must use one shared canonical master",
            )
            keyframe_indices = [frame["index"] for frame in keyframes]
            for frame in in_betweens:
                frame_location = f"{location}.frame[index={frame['index']}]"
                previous = max((value for value in keyframe_indices if value < frame["index"]), default=None)
                following = min((value for value in keyframe_indices if value > frame["index"]), default=None)
                if loop is True:
                    if previous is None and keyframe_indices:
                        previous = max(keyframe_indices)
                    if following is None and keyframe_indices:
                        following = min(keyframe_indices)
                declared_previous = frame.get("previous_keyframe")
                declared_next = frame.get("next_keyframe")
                self.machine(
                    declared_previous == previous and declared_next == following and previous is not None and following is not None,
                    f"{frame_location}.bracketing",
                    f"declared={declared_previous!r}..{declared_next!r}, adjacent-keyframes={previous!r}..{following!r}",
                )
                keyframes_by_index = {item["index"]: item for item in keyframes}
                previous_artifact = keyframes_by_index.get(previous, {}).get("high_resolution")
                following_artifact = keyframes_by_index.get(following, {}).get("high_resolution")
                high_resolution = frame.get("high_resolution")
                target_bracket_relations = [
                    relation
                    for relation in self.relations
                    if relation.get("type") == "adjacent-keyframe-reference"
                    and relation.get("target") == high_resolution
                ]
                bracket_relations = [
                    relation
                    for relation in target_bracket_relations
                    if relation.get("sources") == [previous_artifact, following_artifact]
                ]
                self.machine(
                    previous_artifact != following_artifact
                    and len(target_bracket_relations) == 1
                    and len(bracket_relations) == 1,
                    f"{frame_location}.adjacent-keyframe-reference",
                    f"in-between={high_resolution!r}, expected sources={[previous_artifact, following_artifact]!r}, "
                    f"all target relations={len(target_bracket_relations)}, matching relations={len(bracket_relations)}",
                )
                self.declared(
                    f"{frame_location}.bracketing",
                    "manifest declares adjacent keyframes as creative inputs; use of those inputs is not observable from the output image",
                )

        frame_count = contract.get("frame_count")
        actual_indices = [frame["index"] for frame in all_frames]
        complete_coverage = (
            frame_count is not None
            and len(actual_indices) == frame_count
            and all(index == position for position, index in enumerate(actual_indices))
        )
        self.machine(
            complete_coverage,
            "clips.frames.index",
            f"actual={actual_indices}, expected complete ordered coverage=0..{frame_count - 1 if frame_count is not None else None}",
        )
        targets = [frame.get("target") for frame in all_frames]
        self.machine(
            all(isinstance(target, str) for target in targets)
            and len(targets) == len(set(targets)),
            "clips.frames.target",
            "each target artifact appears in exactly one frame",
        )
        high_resolution_sources = [frame.get("high_resolution") for frame in all_frames]
        self.machine(
            all(isinstance(source, str) for source in high_resolution_sources)
            and len(high_resolution_sources) == len(set(high_resolution_sources)),
            "clips.frames.high_resolution",
            "each high-resolution frame artifact appears in exactly one global frame",
        )
        return all_frames

    def _validate_reviews(self, entries: list[Any]) -> dict[str, list[int]]:
        seen: set[str] = set()
        seen_orders: set[int] = set()
        approved_subjects: dict[str, list[int]] = {}
        for index, raw in enumerate(entries):
            location = f"reviews[{index}]"
            if not isinstance(raw, dict):
                self.machine(False, location, "must be an object")
                continue
            review_id = raw.get("id")
            valid_id = isinstance(review_id, str) and bool(review_id) and review_id not in seen
            self.machine(valid_id, f"{location}.id", f"value={review_id!r}; must be a unique non-empty string")
            if isinstance(review_id, str):
                seen.add(review_id)
            subject = raw.get("subject")
            subject_known = self._known_reference(subject, f"{location}.subject")
            stage = raw.get("stage")
            status = raw.get("status")
            reviewer = raw.get("reviewer")
            subject_type = self.artifacts[subject].get("type") if subject_known else None
            expected_stage = REVIEW_STAGE_BY_TYPE.get(subject_type) if isinstance(subject_type, str) else None
            self.machine(
                expected_stage is not None and stage == expected_stage,
                f"{location}.stage",
                f"value={stage!r}, expected={expected_stage!r} for subject={subject!r}",
            )
            self.machine(status == "approved", f"{location}.status", f"value={status!r}, required='approved'")
            self.machine(isinstance(reviewer, str) and bool(reviewer), f"{location}.reviewer", f"value={reviewer!r}")
            declared_order = self._positive_int(raw.get("declared_order"), f"{location}.declared_order")
            unique_order = declared_order is not None and declared_order not in seen_orders
            self.machine(unique_order, f"{location}.declared_order", f"value={declared_order!r}; must be unique")
            if declared_order is not None:
                seen_orders.add(declared_order)
            self.reviewed(
                location,
                f"manifest records status={status!r}, reviewer={reviewer!r}, declared_order={declared_order!r}; approval authenticity, order, and review quality require human evidence review",
            )
            if status == "approved" and isinstance(subject, str) and declared_order is not None:
                approved_subjects.setdefault(subject, []).append(declared_order)

        review_required = [
            artifact_id
            for artifact_id, artifact in self.artifacts.items()
            if isinstance(artifact.get("type"), str)
            and artifact.get("type")
            in {"canonical-master", "high-resolution-keyframe", "high-resolution-in-between"}
        ]
        for artifact_id in review_required:
            count = len(approved_subjects.get(artifact_id, []))
            self.machine(
                count >= 1,
                f"reviews[subject={artifact_id!r}]",
                f"approved review declarations={count}, required at least 1",
            )
        return approved_subjects

    def _validate_review_order(
        self,
        review_orders: dict[str, list[int]],
        frames: list[dict[str, Any]] | None = None,
    ) -> None:
        canonical_orders = [
            order
            for artifact_id, orders in review_orders.items()
            if self.artifacts.get(artifact_id, {}).get("type") == "canonical-master"
            for order in orders
        ]
        keyframe_orders = [
            order
            for artifact_id, orders in review_orders.items()
            if self.artifacts.get(artifact_id, {}).get("type") == "high-resolution-keyframe"
            for order in orders
        ]
        self.machine(
            bool(canonical_orders) and bool(keyframe_orders) and max(canonical_orders) < min(keyframe_orders),
            "reviews.canonical-before-keyframes",
            f"canonical orders={canonical_orders}, keyframe orders={keyframe_orders}",
        )

        if frames is None:
            return
        clip_ids = {frame.get("_clip_id") for frame in frames}
        for clip_id in sorted(clip_ids, key=str):
            clip_frames = [frame for frame in frames if frame.get("_clip_id") == clip_id]
            clip_keyframe_orders = [
                order
                for frame in clip_frames
                if frame.get("role") == "keyframe"
                for order in review_orders.get(frame.get("high_resolution"), [])
            ]
            clip_in_between_orders = [
                order
                for frame in clip_frames
                if frame.get("role") == "in-between"
                for order in review_orders.get(frame.get("high_resolution"), [])
            ]
            self.machine(
                bool(clip_keyframe_orders)
                and bool(clip_in_between_orders)
                and max(clip_keyframe_orders) < min(clip_in_between_orders),
                f"reviews.clip[{clip_id!r}].keyframes-before-in-betweens",
                f"keyframe orders={clip_keyframe_orders}, in-between orders={clip_in_between_orders}",
            )

    def _validate_transforms(
        self,
        entries: list[Any],
        frames: list[dict[str, Any]],
        review_orders: dict[str, list[int]],
    ) -> None:
        seen: set[str] = set()
        seen_orders = {order for orders in review_orders.values() for order in orders}
        by_target: dict[str, list[dict[str, Any]]] = {}
        for index, raw in enumerate(entries):
            location = f"transforms[{index}]"
            if not isinstance(raw, dict):
                self.machine(False, location, "must be an object")
                continue
            transform_id = raw.get("id")
            valid_id = isinstance(transform_id, str) and bool(transform_id) and transform_id not in seen
            self.machine(valid_id, f"{location}.id", f"value={transform_id!r}; must be a unique non-empty string")
            if isinstance(transform_id, str):
                seen.add(transform_id)
            self.machine(raw.get("type") == "downsample", f"{location}.type", f"value={raw.get('type')!r}, required='downsample'")
            source = raw.get("source")
            target = raw.get("target")
            source_known = self._known_reference(source, f"{location}.source")
            target_known = self._known_reference(target, f"{location}.target")
            if source_known:
                source_type = self.artifacts[source].get("type")
                self.machine(
                    isinstance(source_type, str)
                    and source_type in {"high-resolution-keyframe", "high-resolution-in-between"},
                    f"{location}.source",
                    f"artifact type={source_type!r}; must be a high-resolution frame",
                )
            if target_known:
                target_type = self.artifacts[target].get("type")
                self.machine(target_type == "target-frame", f"{location}.target", f"artifact type={target_type!r}")
            resize_count = raw.get("declared_resize_count")
            self.machine(resize_count == 1, f"{location}.declared_resize_count", f"value={resize_count!r}, required=1")
            declared_order = self._positive_int(raw.get("declared_order"), f"{location}.declared_order")
            unique_order = declared_order is not None and declared_order not in seen_orders
            self.machine(unique_order, f"{location}.declared_order", f"value={declared_order!r}; must follow a unique review order")
            if declared_order is not None:
                seen_orders.add(declared_order)
            if isinstance(target, str):
                by_target.setdefault(target, []).append(raw)
            self.declared(
                location,
                f"manifest declares one downsample from {source!r} to {target!r} at order={declared_order!r}; actual transform count, order, and method are not recoverable from pixels",
            )

        for frame in frames:
            target = frame.get("target")
            source = frame.get("high_resolution")
            declarations = by_target.get(target, []) if isinstance(target, str) else []
            matching = [entry for entry in declarations if entry.get("source") == source]
            self.machine(
                len(declarations) == 1 and len(matching) == 1,
                f"transforms[target={target!r}]",
                f"declarations={len(declarations)}, declarations matching frame source={len(matching)}; required exactly 1",
            )
            if len(matching) == 1:
                clip_id = frame.get("_clip_id")
                clip_frames = [item for item in frames if item.get("_clip_id") == clip_id]
                clip_review_orders = [
                    order
                    for item in clip_frames
                    for order in review_orders.get(item.get("high_resolution"), [])
                ]
                transform_order = matching[0].get("declared_order")
                self.machine(
                    bool(clip_review_orders)
                    and isinstance(transform_order, int)
                    and transform_order > max(clip_review_orders),
                    f"transforms[target={target!r}].after-sequence-review",
                    f"transform order={transform_order!r}, clip review orders={clip_review_orders}",
                )

    def _validate_assembly(
        self,
        assembly: dict[str, Any],
        frames: list[dict[str, Any]],
        contract: dict[str, int | None],
    ) -> None:
        sheet_id = assembly.get("sheet")
        sheet_known = self._known_reference(sheet_id, "assembly.sheet")
        if sheet_known:
            self.machine(
                self.artifacts[sheet_id].get("type") == "spritesheet",
                "assembly.sheet",
                f"artifact type={self.artifacts[sheet_id].get('type')!r}",
            )
        columns = self._positive_int(assembly.get("columns"), "assembly.columns")
        rows = self._positive_int(assembly.get("rows"), "assembly.rows")
        order = assembly.get("order")
        valid_order = isinstance(order, str) and order in {"row-major", "column-major"}
        self.machine(valid_order, "assembly.order", f"value={order!r}")
        targets = assembly.get("targets")
        valid_targets = isinstance(targets, list)
        self.machine(valid_targets, "assembly.targets", "must be an ordered array")
        if not valid_targets:
            return
        expected_targets = [frame.get("target") for frame in frames]
        self.machine(targets == expected_targets, "assembly.targets", f"actual={targets}, clip order={expected_targets}")
        for index, target in enumerate(targets):
            self._known_reference(target, f"assembly.targets[{index}]")
        frame_count = contract.get("frame_count")
        if columns is not None and frame_count is not None:
            expected_rows = (frame_count + columns - 1) // columns
            self.machine(rows == expected_rows, "assembly.rows", f"actual={rows}, expected={expected_rows}")
        width = contract.get("frame_width")
        height = contract.get("frame_height")
        if not (
            sheet_known
            and sheet_id in self.images
            and columns is not None
            and rows is not None
            and width is not None
            and height is not None
            and valid_order
        ):
            return
        sheet = self.images[sheet_id]
        expected_size = (columns * width, rows * height)
        self.machine(sheet.size == expected_size, "assembly.grid-size", f"actual={sheet.size}, expected={expected_size}")
        if sheet.size != expected_size:
            return
        for index, target in enumerate(targets):
            if not isinstance(target, str) or target not in self.images:
                continue
            if order == "row-major":
                column, row = index % columns, index // columns
            else:
                column, row = index // rows, index % rows
            cell = sheet.crop((column * width, row * height, (column + 1) * width, (row + 1) * height))
            target_image = self.images[target]
            equal = target_image.size == (width, height) and target_image.mode == "RGBA" and cell.tobytes() == target_image.tobytes()
            self.machine(
                equal,
                f"assembly.targets[{index}].pixels",
                f"sheet cell=({column},{row}) exactly equals target={target!r}: {equal}",
            )
        used = len(targets)
        unused_clean = True
        for index in range(used, columns * rows):
            if order == "row-major":
                column, row = index % columns, index // columns
            else:
                column, row = index // rows, index % rows
            cell = sheet.crop((column * width, row * height, (column + 1) * width, (row + 1) * height))
            if cell.getchannel("A").getbbox() is not None:
                unused_clean = False
        self.machine(unused_clean, "assembly.unused-cells", "unused fixed-grid cells have zero alpha")

    def _validate_artifact_graph(
        self,
        frames: list[dict[str, Any]],
        transforms: list[Any],
        assembly: dict[str, Any],
    ) -> None:
        def artifacts_of_type(artifact_type: str) -> set[str]:
            return {
                artifact_id
                for artifact_id, artifact in self.artifacts.items()
                if artifact.get("type") == artifact_type
            }

        keyframes = {
            frame["high_resolution"]
            for frame in frames
            if frame.get("role") == "keyframe" and isinstance(frame.get("high_resolution"), str)
        }
        in_betweens = {
            frame["high_resolution"]
            for frame in frames
            if frame.get("role") == "in-between" and isinstance(frame.get("high_resolution"), str)
        }
        targets = {
            frame["target"]
            for frame in frames
            if isinstance(frame.get("target"), str)
        }
        canonical_masters = {
            relation["sources"][0]
            for relation in self.relations
            if relation.get("type") == "canonical-reference"
            and isinstance(relation.get("target"), str)
            and relation.get("target") in keyframes
            and isinstance(relation.get("sources"), list)
            and len(relation["sources"]) == 1
            and isinstance(relation["sources"][0], str)
        }
        pre_masters = {
            relation["sources"][0]
            for relation in self.relations
            if relation.get("type") == "canonical-lock"
            and isinstance(relation.get("target"), str)
            and relation.get("target") in canonical_masters
            and isinstance(relation.get("sources"), list)
            and len(relation["sources"]) == 1
            and isinstance(relation["sources"][0], str)
        }
        sheet = assembly.get("sheet")
        expected_by_type = {
            "high-resolution-pre-master": pre_masters,
            "canonical-master": canonical_masters,
            "high-resolution-keyframe": keyframes,
            "high-resolution-in-between": in_betweens,
            "target-frame": targets,
            "spritesheet": {sheet} if isinstance(sheet, str) else set(),
        }
        for artifact_type, expected in expected_by_type.items():
            actual = artifacts_of_type(artifact_type)
            self.machine(
                actual == expected,
                f"artifact-graph.{artifact_type}",
                f"recorded={sorted(actual)}, consumed by production graph={sorted(expected)}",
            )

        transform_targets = {
            entry.get("target")
            for entry in transforms
            if isinstance(entry, dict) and entry.get("type") == "downsample" and isinstance(entry.get("target"), str)
        }
        self.machine(
            transform_targets == targets,
            "artifact-graph.downsample-targets",
            f"transform targets={sorted(transform_targets)}, frame targets={sorted(targets)}",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a spritesheet lineage manifest and its local image evidence.",
    )
    parser.add_argument("--lineage", required=True, type=Path, help="Path to a spritesheet-lineage/v1 JSON manifest")
    return parser.parse_args()


def load_manifest(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.lineage)
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL MACHINE-VERIFIED manifest: cannot read JSON: {error}")
        return 1

    validator = Validator(args.lineage.resolve())
    validator.validate(data)
    for finding in validator.findings:
        if finding.level == "MACHINE-VERIFIED":
            status = "PASS" if finding.passed else "FAIL"
        else:
            status = "INFO"
        print(f"{status} {finding.level} {finding.location}: {finding.detail}")
    failures = sum(finding.level == "MACHINE-VERIFIED" and finding.passed is False for finding in validator.findings)
    machine_passes = sum(finding.level == "MACHINE-VERIFIED" and finding.passed is True for finding in validator.findings)
    declared = sum(finding.level == "DECLARED" for finding in validator.findings)
    reviewed = sum(finding.level == "REVIEWED" for finding in validator.findings)
    print(
        f"SUMMARY machine_passes={machine_passes} machine_failures={failures} "
        f"declared_history_items={declared} reviewed_claims={reviewed}",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
