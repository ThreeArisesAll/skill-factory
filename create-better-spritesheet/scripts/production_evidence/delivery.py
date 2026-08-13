"""Seal and independently verify closed spritesheet delivery directories."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from .errors import EvidenceError
from .io import (
    BuildBudget,
    atomic_directory,
    canonical_json_bytes,
    canonical_sha256,
    copy_bound_file,
    inspect_tree,
    package_tree_sha256,
    read_bound_json_snapshot,
    read_json,
    reject_path_overlap,
    resolve_job_reference,
    sha256_file,
    verify_file_reference,
    write_canonical_json,
)
from .schemas import (
    BLUEPRINT_SCHEMA,
    DELIVERY_SCHEMA,
    DIAGNOSTICS_SCHEMA,
    IDENTITY_SCHEMA,
    REVIEW_SCHEMA,
    RUNTIME_PROJECTION_SCHEMA,
    RUNTIME_SCHEMA,
    SPACING_SCHEMA,
    validate_delivery,
    validate_document,
)

VERIFY_TIMEOUT_SECONDS = 180


def _verify_package(manifest_path: Path, pipeline_path: Path) -> None:
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(pipeline_path),
                "verify-package",
                "--manifest",
                str(manifest_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=VERIFY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise EvidenceError(
            "PACKAGE_VERIFY_TIMEOUT", "verify-package exceeded its bounded runtime"
        ) from error
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise EvidenceError(
            "PACKAGE_VERIFY_FAILED", detail[-4000:] or "verify-package failed"
        )


def _load_ref(
    value: Any, location: str, schema: str
) -> tuple[Path, str, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location} must contain exactly path and sha256"
        )
    path = Path(value["path"])
    digest, document, raw = read_bound_json_snapshot(path, value["sha256"], location)
    validate_document(document, schema)
    if raw != canonical_json_bytes(document):
        raise EvidenceError(
            "JSON_NOT_CANONICAL", f"{location} must use the canonical JSON serializer"
        )
    return path, digest, document


def _copy_document(document: dict[str, Any], destination: Path) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_canonical_json(destination, document)
    return {"ref": destination.as_posix(), "sha256": sha256_file(destination)}


def _review_subject_hash(review: dict[str, Any]) -> str:
    return canonical_sha256(
        {
            "schema_version": REVIEW_SCHEMA,
            "review_packet_id": review["review_packet_id"],
            "subjects": review["subjects"],
            "evidence": review["evidence"],
            "reviews": review["reviews"],
        },
    )


def _verify_review_assets(review_path: Path, review: dict[str, Any]) -> None:
    for index, item in enumerate(review["evidence"]):
        resolve_job_reference(
            review_path.parent.resolve(),
            {"ref": item["ref"], "sha256": item["sha256"]},
            f"review evidence[{index}]",
        )
    if review["decision"]["subject_sha256"] != _review_subject_hash(review):
        raise EvidenceError(
            "APPROVAL_HASH_MISMATCH",
            "review decision does not bind subjects, evidence, and observations",
        )


def _verify_runtime_assets(runtime_path: Path, proof: dict[str, Any]) -> None:
    for index, item in enumerate(proof["evidence"]):
        resolve_job_reference(
            runtime_path.parent.resolve(),
            {"ref": item["ref"], "sha256": item["sha256"]},
            f"runtime evidence[{index}]",
        )


def _expected_projection(
    manifest: dict[str, Any], manifest_sha256: str, contract_sha256: str
) -> dict[str, Any]:
    contract = manifest["contract"]
    return {
        "schema_version": RUNTIME_PROJECTION_SCHEMA,
        "package_manifest_sha256": manifest_sha256,
        "runtime_contract_sha256": contract_sha256,
        "contract": {
            key: contract[key]
            for key in (
                "frame_width",
                "frame_height",
                "frame_count",
                "animation_origin",
                "anchor",
                "safe_bounds",
            )
        },
        "assembly": {
            key: manifest["assembly"][key]
            for key in ("sheet", "columns", "rows", "order", "cells")
        },
        "clips": [
            {
                key: clip[key]
                for key in (
                    "id",
                    "frame_ids",
                    "durations_ms",
                    "events",
                    "loop",
                    "root_motion",
                    "transition",
                    "terminal_hold",
                )
            }
            for clip in manifest["clips"]
        ],
    }


def _check_projection(
    projection: dict[str, Any],
    manifest: dict[str, Any],
    manifest_sha256: str,
    contract_sha256: str,
) -> None:
    validate_document(projection, RUNTIME_PROJECTION_SCHEMA)
    if projection != _expected_projection(manifest, manifest_sha256, contract_sha256):
        raise EvidenceError(
            "RUNTIME_BINDING_MISMATCH",
            "runtime projection must exactly match the current package and runtime contract",
        )


def _check_runtime_proof(proof: dict[str, Any], manifest: dict[str, Any]) -> None:
    expected_clip_ids = [clip["id"] for clip in manifest["clips"]]
    if proof["playback"]["clip_ids"] != expected_clip_ids:
        raise EvidenceError(
            "RUNTIME_CHECK_FAILED",
            "runtime proof clip_ids must exactly cover manifest clips in order",
        )
    expected_events = [
        {
            "name": event["name"],
            "clip_id": clip["id"],
            "position": event["position"],
            "observed": True,
        }
        for clip in manifest["clips"]
        for event in clip["events"]
    ]
    if proof["events"] != expected_events:
        raise EvidenceError(
            "RUNTIME_CHECK_FAILED",
            "runtime proof events must exactly cover manifest events and be observed",
        )
    if not proof["evidence"] or not proof["rendering"]["checks_passed"]:
        raise EvidenceError(
            "RUNTIME_CHECK_FAILED",
            "runtime proof requires evidence and passing rendering checks",
        )


def _validate_evidence_bindings(
    manifest: dict[str, Any],
    identity: dict[str, Any],
    blueprints: list[dict[str, Any]],
    spacings: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> None:
    artifacts = {artifact["id"]: artifact for artifact in manifest["artifacts"]}
    admissions = {
        admission["canonical_reference"]: admission
        for admission in manifest["canonical_admissions"]
    }
    expected_identity = {
        (clip["canonical_reference"], clip["direction"], clip["camera"]): (
            artifacts[clip["canonical_reference"]]["sha256"],
            admissions[clip["canonical_reference"]]["proof_sha256"],
        )
        for clip in manifest["clips"]
    }
    actual_identity: dict[tuple[str, str, str], tuple[str, str]] = {}
    for binding in identity["content"]["canonical_bindings"]:
        key = (binding["canonical_id"], binding["direction"], binding["camera"])
        if key in actual_identity:
            raise EvidenceError(
                "IDENTITY_BINDING_MISMATCH",
                "identity bible contains a duplicate canonical binding",
            )
        actual_identity[key] = (
            binding["candidate_sha256"],
            binding["admission_proof_sha256"],
        )
    if actual_identity != expected_identity:
        raise EvidenceError(
            "IDENTITY_BINDING_MISMATCH",
            "identity bible must exactly bind each package canonical, direction, camera, candidate, and admission proof",
        )

    clips = {clip["id"]: clip for clip in manifest["clips"]}
    if len(blueprints) != len(clips) or len(
        {blueprint["content"]["clip_id"] for blueprint in blueprints}
    ) != len(clips):
        raise EvidenceError(
            "BLUEPRINT_COVERAGE_MISMATCH",
            "motion blueprints must cover every package clip exactly once",
        )
    blueprints_by_clip = {
        blueprint["content"]["clip_id"]: blueprint for blueprint in blueprints
    }
    spacings_by_clip = {spacing["content"]["clip_id"]: spacing for spacing in spacings}
    if len(spacings) != len(clips) or len(spacings_by_clip) != len(clips):
        raise EvidenceError(
            "SPACING_COVERAGE_MISMATCH",
            "spacing plans must cover every package clip exactly once",
        )
    cell_cursor = 0
    expected_diagnostics: dict[str, list[tuple[int, str]]] = {}
    for clip in manifest["clips"]:
        blueprint = blueprints_by_clip[clip["id"]]
        content = blueprint["content"]
        spacing = spacings_by_clip[clip["id"]]
        if spacing["content"]["motion_blueprint_sha256"] != canonical_sha256(blueprint):
            raise EvidenceError(
                "SPACING_BINDING_MISMATCH",
                f"spacing plan {clip['id']!r} does not bind its current motion blueprint",
            )
        for key in (
            "canonical_reference",
            "direction",
            "camera",
            "loop",
            "root_motion",
        ):
            blueprint_key = "canonical_id" if key == "canonical_reference" else key
            if content[blueprint_key] != clip[key]:
                raise EvidenceError(
                    "BLUEPRINT_BINDING_MISMATCH",
                    f"motion blueprint {content['clip_id']!r} does not match package {key}",
                )
        expected_keyframes = [
            frame_id
            for frame_id in clip["frame_ids"]
            if artifacts[frame_id]["role"] == "keyframe"
        ]
        if [
            position["frame_id"] for position in content["positions"]
        ] != expected_keyframes:
            raise EvidenceError(
                "BLUEPRINT_BINDING_MISMATCH",
                f"motion blueprint {content['clip_id']!r} must contain structural keyframes only",
            )
        approved_keyframes = {
            item["frame_id"]: item["source_sha256"]
            for item in spacing["content"]["approved_keyframes"]
        }
        if approved_keyframes != {
            frame_id: artifacts[frame_id]["sha256"] for frame_id in expected_keyframes
        }:
            raise EvidenceError(
                "SPACING_BINDING_MISMATCH",
                f"spacing plan {clip['id']!r} approved keyframe hashes are stale",
            )
        positions = spacing["content"]["positions"]
        if len(positions) != len(clip["durations_ms"]):
            raise EvidenceError(
                "SPACING_BINDING_MISMATCH",
                f"spacing plan {content['clip_id']!r} position count is stale",
            )
        for local_index, position in enumerate(positions):
            cell = manifest["assembly"]["cells"][cell_cursor + local_index]
            expected_role = (
                "closing-alias"
                if cell["repeated_opening"]
                else artifacts[cell["source"]]["role"]
            )
            if (
                position["index"] != local_index
                or position["frame_id"] != cell["source"]
                or position["duration_ms"] != clip["durations_ms"][local_index]
                or position["role"] != expected_role
            ):
                raise EvidenceError(
                    "SPACING_BINDING_MISMATCH",
                    f"spacing plan {content['clip_id']!r} position {local_index} is stale",
                )
            expected_events = sorted(
                event["name"]
                for event in clip["events"]
                if event["position"] == local_index
            )
            if sorted(position["events"]) != expected_events:
                raise EvidenceError(
                    "SPACING_BINDING_MISMATCH",
                    f"spacing plan {content['clip_id']!r} events are stale",
                )
        expected_diagnostics[clip["id"]] = [
            (
                cell_cursor + offset,
                manifest["assembly"]["cells"][cell_cursor + offset]["source"],
            )
            for offset in range(len(positions))
        ]
        cell_cursor += len(positions)
    actual_diagnostics = {
        clip["clip_id"]: [(cell["index"], cell["source"]) for cell in clip["cells"]]
        for clip in diagnostics["clips"]
    }
    if actual_diagnostics != expected_diagnostics:
        raise EvidenceError(
            "DIAGNOSTICS_BINDING_MISMATCH",
            "motion diagnostics must cover every package cell in manifest order",
        )


def seal_delivery(request_path: Path, output_dir: Path, pipeline_path: Path) -> None:
    request = read_json(request_path, "delivery request")
    if request.get("schema_version") != DELIVERY_SCHEMA:
        raise EvidenceError(
            "SCHEMA_VERSION_UNSUPPORTED", f"schema_version must be {DELIVERY_SCHEMA!r}"
        )
    validate_delivery(request, request=True)
    _, identity_hash, identity = _load_ref(
        request["identity_bible"], "identity bible", IDENTITY_SCHEMA
    )
    if identity["approval"]["status"] != "approved":
        raise EvidenceError("APPROVAL_REQUIRED", "identity bible must be approved")
    blueprint_inputs: list[tuple[Path, str, dict[str, Any]]] = []
    for index, reference in enumerate(request["motion_blueprints"]):
        blueprint_path, blueprint_hash, blueprint = _load_ref(
            reference, f"motion blueprint[{index}]", BLUEPRINT_SCHEMA
        )
        if blueprint["approval"]["status"] != "approved":
            raise EvidenceError(
                "APPROVAL_REQUIRED", f"motion blueprint[{index}] must be approved"
            )
        if blueprint["content"]["identity_bible_sha256"] != identity_hash:
            raise EvidenceError(
                "HASH_MISMATCH",
                f"motion blueprint[{index}] does not bind the current identity bible",
            )
        blueprint_inputs.append((blueprint_path, blueprint_hash, blueprint))
    spacing_inputs: list[tuple[Path, str, dict[str, Any]]] = []
    for index, reference in enumerate(request["spacing_plans"]):
        spacing_path, spacing_hash, spacing = _load_ref(
            reference, f"spacing plan[{index}]", SPACING_SCHEMA
        )
        if spacing["approval"]["status"] != "approved":
            raise EvidenceError(
                "APPROVAL_REQUIRED", f"spacing plan[{index}] must be approved"
            )
        spacing_inputs.append((spacing_path, spacing_hash, spacing))
    diagnostics_path, diagnostics_hash, diagnostics = _load_ref(
        request["motion_diagnostics"], "motion diagnostics", DIAGNOSTICS_SCHEMA
    )
    review_path, _, review = _load_ref(
        request["review_packet"], "review packet", REVIEW_SCHEMA
    )
    _verify_review_assets(review_path, review)
    if review["decision"]["status"] != "approved":
        raise EvidenceError(
            "APPROVAL_REQUIRED", "review packet decision must be approved"
        )
    manifest_path, manifest_hash = verify_file_reference(
        request["pixel_package"]["manifest"], "pixel package manifest"
    )
    if manifest_path.name != "manifest.json":
        raise EvidenceError(
            "PACKAGE_INVALID", "pixel package manifest must be named manifest.json"
        )
    _verify_package(manifest_path, pipeline_path)
    actual_tree_hash = package_tree_sha256(manifest_path.parent)
    if request["pixel_package"]["package_tree_sha256"] != actual_tree_hash:
        raise EvidenceError("HASH_MISMATCH", "pixel package tree hash does not match")
    if diagnostics["package_manifest"]["sha256"] != manifest_hash:
        raise EvidenceError(
            "HASH_MISMATCH",
            "motion diagnostics does not bind the current package manifest",
        )
    manifest = read_json(manifest_path, "pixel package manifest")
    clip_ids = {clip["id"] for clip in manifest["clips"]}
    blueprint_clip_ids = {item[2]["content"]["clip_id"] for item in blueprint_inputs}
    if blueprint_clip_ids != clip_ids:
        raise EvidenceError(
            "BLUEPRINT_COVERAGE_MISMATCH",
            "motion blueprints must cover every package clip exactly",
        )
    _validate_evidence_bindings(
        manifest,
        identity,
        [item[2] for item in blueprint_inputs],
        [item[2] for item in spacing_inputs],
        diagnostics,
    )
    expected_subject_hashes = {
        identity_hash,
        diagnostics_hash,
        manifest_hash,
        *(item[1] for item in blueprint_inputs),
        *(item[1] for item in spacing_inputs),
    }
    reviewed_hashes = {subject["sha256"] for subject in review["subjects"]}
    if not expected_subject_hashes.issubset(reviewed_hashes):
        raise EvidenceError(
            "REVIEW_COVERAGE_MISMATCH",
            "review packet must bind identity, blueprints, diagnostics, and package manifest",
        )
    required_subject_ids = {
        subject["id"]
        for subject in review["subjects"]
        if subject["sha256"] in expected_subject_hashes
    }
    acceptable_subject_ids = {
        observation["subject_id"]
        for review_record in review["reviews"]
        for observation in review_record["observations"]
        if observation["disposition"] == "acceptable"
    }
    if required_subject_ids != acceptable_subject_ids.intersection(
        required_subject_ids
    ):
        raise EvidenceError(
            "REVIEW_COVERAGE_MISMATCH",
            "every required delivery subject needs an acceptable review observation",
        )

    runtime_request = request["runtime"]
    runtime_sources: dict[str, tuple[Path, str] | None] = {}
    runtime_sources["contract"] = (
        None
        if runtime_request["contract"] is None
        else verify_file_reference(runtime_request["contract"], "runtime contract")
    )
    projection_input: tuple[Path, str, dict[str, Any]] | None = None
    if runtime_request["projection"] is not None:
        projection_input = _load_ref(
            runtime_request["projection"],
            "runtime projection",
            RUNTIME_PROJECTION_SCHEMA,
        )
    runtime_sources["projection"] = (
        None if projection_input is None else projection_input[:2]
    )
    runtime_proof_input: tuple[Path, str, dict[str, Any]] | None = None
    if runtime_request["proof"] is not None:
        runtime_proof_input = _load_ref(
            runtime_request["proof"], "runtime proof", RUNTIME_SCHEMA
        )
        _verify_runtime_assets(runtime_proof_input[0], runtime_proof_input[2])
    if runtime_sources["projection"] is not None:
        if runtime_sources["contract"] is None:
            raise EvidenceError(
                "RUNTIME_BINDING_MISMATCH",
                "runtime projection requires runtime contract",
            )
        assert projection_input is not None
        _check_projection(
            projection_input[2],
            manifest,
            manifest_hash,
            runtime_sources["contract"][1],
        )
    if runtime_proof_input is not None:
        proof = runtime_proof_input[2]
        if proof["package_manifest_sha256"] != manifest_hash:
            raise EvidenceError(
                "RUNTIME_BINDING_MISMATCH",
                "runtime proof does not bind the current package manifest",
            )
        if (
            runtime_sources["contract"] is None
            or proof["runtime_contract_sha256"] != runtime_sources["contract"][1]
        ):
            raise EvidenceError(
                "RUNTIME_BINDING_MISMATCH",
                "runtime proof does not bind the current runtime contract",
            )
    if request["status"] == "runtime-verified":
        assert runtime_proof_input is not None
        proof = runtime_proof_input[2]
        _check_runtime_proof(proof, manifest)

    input_paths = [
        request_path,
        manifest_path.parent,
        diagnostics_path.parent,
        review_path,
        *[item[0] for item in blueprint_inputs],
        *[item[0] for item in spacing_inputs],
        *[record[0] for record in runtime_sources.values() if record is not None],
    ]
    if runtime_proof_input is not None:
        input_paths.append(runtime_proof_input[0])
    reject_path_overlap(output_dir, input_paths)

    def build(destination: Path) -> None:
        budget = BuildBudget()

        def budgeted_document(document: dict[str, Any], target: Path) -> None:
            budget.reserve(
                len(canonical_json_bytes(document)),
                target.relative_to(destination).as_posix(),
            )
            _copy_document(document, target)

        def budgeted_copy(source: Path, target: Path, digest: str) -> None:
            copy_bound_file(
                source,
                target,
                digest,
                budget=budget,
                budget_location=target.relative_to(destination).as_posix(),
            )

        package_destination = destination / "package"
        for source in inspect_tree(manifest_path.parent):
            relative = source.relative_to(manifest_path.parent)
            budgeted_copy(
                source,
                package_destination / relative,
                sha256_file(source),
            )
        if package_tree_sha256(package_destination) != actual_tree_hash:
            raise EvidenceError(
                "COPY_VERIFY_FAILED", "copied package tree hash changed"
            )
        evidence_destination = destination / "evidence"
        identity_destination = evidence_destination / "identity-bible.json"
        budgeted_document(identity, identity_destination)
        blueprint_refs: list[dict[str, str]] = []
        for index, (_, _, blueprint) in enumerate(blueprint_inputs):
            target = evidence_destination / "motion-blueprints" / f"{index:04d}.json"
            budgeted_document(blueprint, target)
            blueprint_refs.append(
                {
                    "ref": target.relative_to(destination).as_posix(),
                    "sha256": sha256_file(target),
                }
            )
        spacing_refs: list[dict[str, str]] = []
        for index, (_, _, spacing) in enumerate(spacing_inputs):
            target = evidence_destination / "spacing-plans" / f"{index:04d}.json"
            budgeted_document(spacing, target)
            spacing_refs.append(
                {
                    "ref": target.relative_to(destination).as_posix(),
                    "sha256": sha256_file(target),
                }
            )
        diagnostics_destination = evidence_destination / "motion-diagnostics"
        diagnostics_destination.mkdir(parents=True)
        diagnostics_document = diagnostics_destination / diagnostics_path.name
        budgeted_copy(diagnostics_path, diagnostics_document, diagnostics_hash)
        for location, reference in (
            ("package_manifest", diagnostics["package_manifest"]),
            *(
                (f"assets.{key}", reference)
                for key, reference in diagnostics["assets"].items()
            ),
            *(
                (f"previews[{index}]", preview["asset"])
                for index, preview in enumerate(diagnostics["previews"])
            ),
        ):
            source, _ = resolve_job_reference(
                diagnostics_path.parent.resolve(),
                reference,
                f"motion diagnostics.{location}",
            )
            relative = Path(reference["ref"])
            target = diagnostics_destination / relative
            budgeted_copy(source, target, reference["sha256"])
        if sha256_file(diagnostics_document) != diagnostics_hash:
            raise EvidenceError("COPY_VERIFY_FAILED", "copied diagnostics hash changed")
        review_root = evidence_destination / "review"
        for index, item in enumerate(review["evidence"]):
            source, _ = resolve_job_reference(
                review_path.parent.resolve(),
                {"ref": item["ref"], "sha256": item["sha256"]},
                f"review evidence[{index}]",
            )
            target = review_root / item["ref"]
            target.parent.mkdir(parents=True, exist_ok=True)
            budgeted_copy(source, target, item["sha256"])
        review_destination = review_root / "review-packet.json"
        budgeted_document(review, review_destination)
        runtime_output: dict[str, Any] = {
            "scope": runtime_request["scope"],
            "contract": None,
            "projection": None,
            "proof": None,
        }
        runtime_dir = destination / "runtime"
        for key in ("contract", "projection"):
            source_record = runtime_sources[key]
            if source_record is not None:
                source, _ = source_record
                target = runtime_dir / f"{key}{source.suffix.lower() or '.json'}"
                budgeted_copy(source, target, source_record[1])
                runtime_output[key] = {
                    "ref": target.relative_to(destination).as_posix(),
                    "sha256": sha256_file(target),
                }
        if runtime_proof_input is not None:
            proof_path, _, proof = runtime_proof_input
            for index, item in enumerate(proof["evidence"]):
                source, _ = resolve_job_reference(
                    proof_path.parent.resolve(),
                    {"ref": item["ref"], "sha256": item["sha256"]},
                    f"runtime evidence[{index}]",
                )
                target = runtime_dir / item["ref"]
                target.parent.mkdir(parents=True, exist_ok=True)
                budgeted_copy(source, target, item["sha256"])
            proof_destination = runtime_dir / "runtime-playback-proof.json"
            budgeted_document(proof, proof_destination)
            runtime_output["proof"] = {
                "ref": proof_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(proof_destination),
            }
        delivery = {
            "schema_version": DELIVERY_SCHEMA,
            "job_id": request["job_id"],
            "status": request["status"],
            "identity_bible": {
                "ref": identity_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(identity_destination),
            },
            "motion_blueprints": blueprint_refs,
            "spacing_plans": spacing_refs,
            "pixel_package": {
                "manifest": {
                    "ref": "package/manifest.json",
                    "sha256": sha256_file(package_destination / "manifest.json"),
                },
                "package_tree_sha256": actual_tree_hash,
            },
            "motion_diagnostics": {
                "ref": diagnostics_document.relative_to(destination).as_posix(),
                "sha256": sha256_file(diagnostics_document),
            },
            "review_packet": {
                "ref": review_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(review_destination),
            },
            "runtime": runtime_output,
            "files": [
                {
                    "ref": path.relative_to(destination).as_posix(),
                    "sha256": sha256_file(path),
                }
                for path in inspect_tree(destination)
            ],
        }
        validate_document(delivery, DELIVERY_SCHEMA)
        staged_delivery = destination / "delivery.json"
        budget.reserve(len(canonical_json_bytes(delivery)), "delivery.json")
        write_canonical_json(staged_delivery, delivery)
        report = verification_report(staged_delivery, pipeline_path)
        if not report["passed"]:
            error = report.get("error") or {}
            raise EvidenceError(
                "STAGING_VERIFY_FAILED",
                str(error.get("message", "staged delivery verification failed")),
            )

    atomic_directory(output_dir, build)


def verification_report(delivery_path: Path, pipeline_path: Path) -> dict[str, Any]:
    results: list[dict[str, str]] = []

    def record(classification: str, subject: str, detail: str) -> None:
        results.append(
            {
                "classification": classification,
                "status": "PASS",
                "subject": subject,
                "detail": detail,
            }
        )

    try:
        delivery = read_json(delivery_path, "delivery")
        validate_document(delivery, DELIVERY_SCHEMA)
        root = delivery_path.parent.resolve()
        declared_files = {item["ref"]: item["sha256"] for item in delivery["files"]}
        actual_files = {
            path.relative_to(root).as_posix(): sha256_file(path)
            for path in inspect_tree(root)
            if path.resolve() != delivery_path.resolve()
        }
        if actual_files != declared_files:
            raise EvidenceError(
                "DELIVERY_TREE_MISMATCH",
                "delivery root files must exactly match the content-addressed file list",
            )
        manifest_path, manifest_hash = resolve_job_reference(
            root, delivery["pixel_package"]["manifest"], "pixel package manifest"
        )
        _verify_package(manifest_path, pipeline_path)
        if (
            package_tree_sha256(manifest_path.parent)
            != delivery["pixel_package"]["package_tree_sha256"]
        ):
            raise EvidenceError(
                "HASH_MISMATCH", "sealed package tree hash does not match"
            )
        manifest = read_json(manifest_path, "pixel package manifest")
        record(
            "MACHINE-VERIFIED",
            "pixel-package",
            "v4 replay, manifest hash, closed tree, and sorted tree hash pass",
        )
        identity_path, identity_hash = resolve_job_reference(
            root, delivery["identity_bible"], "identity bible"
        )
        identity = read_json(identity_path, "identity bible")
        validate_document(identity, IDENTITY_SCHEMA)
        if identity["approval"]["status"] != "approved":
            raise EvidenceError(
                "APPROVAL_REQUIRED", "identity bible approval is not approved"
            )
        record(
            "REVIEWED",
            "identity-bible",
            "approved content hash and reviewer record are current",
        )
        blueprint_hashes: list[str] = []
        blueprint_documents: list[dict[str, Any]] = []
        for index, reference in enumerate(delivery["motion_blueprints"]):
            path, digest = resolve_job_reference(
                root, reference, f"motion blueprint[{index}]"
            )
            blueprint = read_json(path, f"motion blueprint[{index}]")
            validate_document(blueprint, BLUEPRINT_SCHEMA)
            if blueprint["approval"]["status"] != "approved":
                raise EvidenceError(
                    "APPROVAL_REQUIRED",
                    f"motion blueprint[{index}] approval is not approved",
                )
            if blueprint["content"]["identity_bible_sha256"] != identity_hash:
                raise EvidenceError(
                    "HASH_MISMATCH",
                    f"motion blueprint[{index}] identity binding is stale",
                )
            blueprint_hashes.append(digest)
            blueprint_documents.append(blueprint)
        spacing_hashes: list[str] = []
        spacing_documents: list[dict[str, Any]] = []
        for index, reference in enumerate(delivery["spacing_plans"]):
            path, digest = resolve_job_reference(
                root, reference, f"spacing plan[{index}]"
            )
            spacing = read_json(path, f"spacing plan[{index}]")
            validate_document(spacing, SPACING_SCHEMA)
            if spacing["approval"]["status"] != "approved":
                raise EvidenceError(
                    "APPROVAL_REQUIRED",
                    f"spacing plan[{index}] approval is not approved",
                )
            spacing_hashes.append(digest)
            spacing_documents.append(spacing)
        record(
            "DECLARED",
            "motion-blueprints",
            "motion intent, topology, timing, and relationships are declared",
        )
        diagnostics_path, _ = resolve_job_reference(
            root, delivery["motion_diagnostics"], "motion diagnostics"
        )
        diagnostics = read_json(diagnostics_path, "motion diagnostics")
        validate_document(diagnostics, DIAGNOSTICS_SCHEMA)
        if diagnostics["package_manifest"]["sha256"] != manifest_hash:
            raise EvidenceError(
                "HASH_MISMATCH", "motion diagnostics package binding is stale"
            )
        resolve_job_reference(
            diagnostics_path.parent.resolve(),
            diagnostics["package_manifest"],
            "motion diagnostics package manifest",
        )
        _validate_evidence_bindings(
            manifest,
            identity,
            blueprint_documents,
            spacing_documents,
            diagnostics,
        )
        for key, reference in diagnostics["assets"].items():
            resolve_job_reference(
                diagnostics_path.parent.resolve(),
                reference,
                f"motion diagnostics asset {key}",
            )
        for index, preview in enumerate(diagnostics["previews"]):
            resolve_job_reference(
                diagnostics_path.parent.resolve(),
                preview["asset"],
                f"motion diagnostics preview[{index}]",
            )
        record(
            "SUPPLIED",
            "motion-diagnostics",
            "sealed diagnostic records and asset hashes pass; measurements are not recomputed and no motion-quality claim is inferred",
        )
        review_path, _ = resolve_job_reference(
            root, delivery["review_packet"], "review packet"
        )
        review = read_json(review_path, "review packet")
        validate_document(review, REVIEW_SCHEMA)
        _verify_review_assets(review_path, review)
        if review["decision"]["status"] != "approved":
            raise EvidenceError(
                "APPROVAL_REQUIRED", "review packet decision is not approved"
            )
        expected = {
            manifest_hash,
            identity_hash,
            *blueprint_hashes,
            *spacing_hashes,
            delivery["motion_diagnostics"]["sha256"],
        }
        if not expected.issubset({subject["sha256"] for subject in review["subjects"]}):
            raise EvidenceError(
                "REVIEW_COVERAGE_MISMATCH",
                "review subjects do not cover the sealed evidence",
            )
        record(
            "REVIEWED",
            "review-packet",
            "review subjects, presentation evidence, observations, and decision are hash-bound",
        )
        runtime = delivery["runtime"]
        if runtime["contract"] is not None:
            _, contract_hash = resolve_job_reference(
                root, runtime["contract"], "runtime contract"
            )
            projection_path, projection_hash = resolve_job_reference(
                root, runtime["projection"], "runtime projection"
            )
            _, projection, _ = read_bound_json_snapshot(
                projection_path, projection_hash, "runtime projection"
            )
            _check_projection(projection, manifest, manifest_hash, contract_hash)
            record(
                "DECLARED",
                "runtime-metadata",
                "runtime contract and package projection are present and bound",
            )
        else:
            contract_hash = None
        if runtime["proof"] is not None:
            proof_path, proof_hash = resolve_job_reference(
                root, runtime["proof"], "runtime proof"
            )
            _, proof, _ = read_bound_json_snapshot(
                proof_path, proof_hash, "runtime proof"
            )
            validate_document(proof, RUNTIME_SCHEMA)
            _verify_runtime_assets(proof_path, proof)
            if (
                proof["package_manifest_sha256"] != manifest_hash
                or proof["runtime_contract_sha256"] != contract_hash
            ):
                raise EvidenceError(
                    "RUNTIME_BINDING_MISMATCH", "runtime proof binding is stale"
                )
            if delivery["status"] == "runtime-verified":
                _check_runtime_proof(proof, manifest)
            record(
                "SUPPLIED",
                "runtime-playback-proof",
                "target runtime playback evidence was supplied and its bindings pass",
            )
        semantic_files = {
            path.relative_to(root).as_posix()
            for path in inspect_tree(manifest_path.parent)
        }
        semantic_files.update(
            {
                delivery["identity_bible"]["ref"],
                delivery["motion_diagnostics"]["ref"],
                delivery["review_packet"]["ref"],
                *(item["ref"] for item in delivery["motion_blueprints"]),
                *(item["ref"] for item in delivery["spacing_plans"]),
            }
        )
        diagnostics_base = Path(delivery["motion_diagnostics"]["ref"]).parent
        semantic_files.add(
            (diagnostics_base / diagnostics["package_manifest"]["ref"]).as_posix()
        )
        semantic_files.update(
            (diagnostics_base / item["ref"]).as_posix()
            for item in diagnostics["assets"].values()
        )
        semantic_files.update(
            (diagnostics_base / item["asset"]["ref"]).as_posix()
            for item in diagnostics["previews"]
        )
        review_base = Path(delivery["review_packet"]["ref"]).parent
        semantic_files.update(
            (review_base / item["ref"]).as_posix() for item in review["evidence"]
        )
        for key in ("contract", "projection", "proof"):
            if runtime[key] is not None:
                semantic_files.add(runtime[key]["ref"])
        if runtime["proof"] is not None:
            proof_base = Path(runtime["proof"]["ref"]).parent
            semantic_files.update(
                (proof_base / item["ref"]).as_posix() for item in proof["evidence"]
            )
        if set(actual_files) != semantic_files:
            raise EvidenceError(
                "DELIVERY_TREE_MISMATCH",
                "delivery root contains files outside semantic evidence references",
            )
        record(
            "MACHINE-VERIFIED",
            "delivery-state",
            f"evidence requirements for {delivery['status']} pass",
        )
        passed = True
        error = None
    except (
        EvidenceError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
    ) as failure:
        passed = False
        code = (
            failure.code
            if isinstance(failure, EvidenceError)
            else "VERIFICATION_FAILED"
        )
        error = {"code": code, "message": str(failure)}
        results.append(
            {
                "classification": "MACHINE-VERIFIED",
                "status": "FAIL",
                "subject": "delivery",
                "detail": str(failure),
            }
        )
    return {
        "schema_version": "spritesheet-delivery-verification-report/v1",
        "delivery": str(delivery_path),
        "passed": passed,
        "results": results,
        "error": error,
    }
