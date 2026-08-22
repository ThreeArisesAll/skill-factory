"""Seal and replay the v2 production evidence closure around a v5 pixel package."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .diagnostics import recompute_motion_metrics
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
    DELIVERY_SCHEMA_V2,
    DIAGNOSTICS_SCHEMA_V2,
    IDENTITY_SCHEMA_V2,
    MOTION_PLAN_SCHEMA_V2,
    RAW_FRAME_ADMISSION_SCHEMA,
    REVIEW_SCHEMA,
    validate_delivery_v2,
    validate_document,
)


def _load_ref(
    value: Any,
    location: str,
    schema: str,
) -> tuple[Path, str, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location} must contain exactly path and sha256"
        )
    path = Path(value["path"])
    digest, document, raw = read_bound_json_snapshot(
        path, value["sha256"], location
    )
    validate_document(document, schema)
    if raw != canonical_json_bytes(document):
        raise EvidenceError(
            "JSON_NOT_CANONICAL", f"{location} must use the canonical JSON serializer"
        )
    return path, digest, document


def _review_subject_hash(review: dict[str, Any]) -> str:
    return canonical_sha256(
        {
            "schema_version": REVIEW_SCHEMA,
            "review_packet_id": review["review_packet_id"],
            "subjects": review["subjects"],
            "evidence": review["evidence"],
            "reviews": review["reviews"],
        }
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


def _plan_positions(
    motion_plan: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    positions: dict[str, dict[str, Any]] = {}
    clips: dict[str, dict[str, Any]] = {}
    for clip in motion_plan["content"]["clips"]:
        clips[clip["id"]] = clip
        for position in clip["positions"]:
            positions[position["id"]] = position
    return positions, clips


def _manifest_artifacts(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {artifact["id"]: artifact for artifact in manifest["artifacts"]}


def _validate_identity_binding(
    identity: dict[str, Any], manifest: dict[str, Any]
) -> None:
    artifacts = _manifest_artifacts(manifest)
    admissions = {
        item["canonical_reference"]: item for item in manifest["canonical_admissions"]
    }
    for view in identity["content"]["canonical_views"]:
        canonical_id = view["canonical_id"]
        artifact = artifacts.get(canonical_id)
        admission = admissions.get(canonical_id)
        if (
            artifact is None
            or artifact.get("type") != "canonical-reference"
            or artifact.get("sha256") != view["candidate_sha256"]
            or admission is None
            or admission.get("proof_sha256") != view["admission_proof_sha256"]
        ):
            raise EvidenceError(
                "IDENTITY_BINDING_MISMATCH",
                f"identity canonical view {canonical_id!r} is stale",
            )
    if {item["canonical_id"] for item in identity["content"]["canonical_views"]} != set(
        admissions
    ):
        raise EvidenceError(
            "IDENTITY_BINDING_MISMATCH",
            "identity canonical views must exactly cover package canonical admissions",
        )


def _expected_manifest_positions(plan_clip: dict[str, Any]) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for position in plan_clip["positions"]:
        if position["role"] == "alias":
            positions.append(
                {
                    "id": position["id"],
                    "role": "alias",
                    "source": position["alias_of"],
                    "alias_kind": position["alias_kind"],
                }
            )
        else:
            positions.append(
                {
                    "id": position["id"],
                    "role": position["role"],
                    "source": position["id"],
                }
            )
    return positions


def _validate_plan_binding(
    motion_plan: dict[str, Any], manifest: dict[str, Any]
) -> None:
    if manifest.get("schema_version") != "spritesheet-package/v5":
        raise EvidenceError(
            "SCHEMA_VERSION_UNSUPPORTED", "delivery/v2 requires spritesheet-package/v5"
        )
    plan_clips = motion_plan["content"]["clips"]
    if [clip["id"] for clip in plan_clips] != [clip["id"] for clip in manifest["clips"]]:
        raise EvidenceError(
            "MOTION_PLAN_BINDING_MISMATCH",
            "motion plan and package clip order must match exactly",
        )
    for plan_clip, package_clip in zip(plan_clips, manifest["clips"], strict=True):
        expected_scalars = {
            "canonical_reference": plan_clip["canonical_view"],
            "direction": plan_clip["direction"],
            "camera": plan_clip["camera"],
            "loop": plan_clip["loop"],
            "root_motion": plan_clip["root_motion"],
            "transition": plan_clip["transition"],
            "terminal_hold": plan_clip["terminal_hold"],
        }
        if any(package_clip.get(key) != value for key, value in expected_scalars.items()):
            raise EvidenceError(
                "MOTION_PLAN_BINDING_MISMATCH",
                f"package clip {plan_clip['id']!r} metadata is stale",
            )
        if package_clip.get("positions") != _expected_manifest_positions(plan_clip):
            raise EvidenceError(
                "MOTION_PLAN_BINDING_MISMATCH",
                f"package clip {plan_clip['id']!r} positions are stale",
            )
        if package_clip.get("durations_ms") != [
            position["duration_ms"] for position in plan_clip["positions"]
        ]:
            raise EvidenceError(
                "MOTION_PLAN_BINDING_MISMATCH",
                f"package clip {plan_clip['id']!r} timing is stale",
            )
        expected_events = [
            {"name": event, "position": index}
            for index, position in enumerate(plan_clip["positions"])
            for event in position["events"]
        ]
        if package_clip.get("events") != expected_events:
            raise EvidenceError(
                "MOTION_PLAN_BINDING_MISMATCH",
                f"package clip {plan_clip['id']!r} events are stale",
            )


def _validate_raw_admissions(
    admissions: list[dict[str, Any]],
    motion_plan: dict[str, Any],
    motion_plan_hash: str,
    manifest: dict[str, Any],
    manifest_path: Path,
    quality_policy: dict[str, Any],
) -> None:
    plan_positions, plan_clips = _plan_positions(motion_plan)
    concrete_ids = {
        position_id
        for position_id, position in plan_positions.items()
        if position["role"] != "alias"
    }
    if {item["frame_id"] for item in admissions} != concrete_ids or len(admissions) != len(
        concrete_ids
    ):
        raise EvidenceError(
            "RAW_FRAME_COVERAGE_MISMATCH",
            "raw frame admissions must cover every concrete motion-plan source exactly once",
        )
    artifacts = _manifest_artifacts(manifest)
    canonical_by_position = {
        position["id"]: clip["canonical_view"]
        for clip in plan_clips.values()
        for position in clip["positions"]
    }
    for admission in admissions:
        frame_id = admission["frame_id"]
        position = plan_positions[frame_id]
        position_without_index = {
            key: value for key, value in position.items() if key != "index"
        }
        artifact = artifacts.get(frame_id)
        if (
            admission["canonical_view"] != canonical_by_position[frame_id]
            or admission["plan_binding"]["motion_plan_sha256"] != motion_plan_hash
            or admission["plan_binding"]["position_sha256"]
            != canonical_sha256(position_without_index)
            or artifact is None
            or artifact.get("type") != "high-resolution-frame-source"
            or artifact.get("sha256") != admission["source"]["sha256"]
            or artifact.get("width") != admission["source"]["width"]
            or artifact.get("height") != admission["source"]["height"]
        ):
            raise EvidenceError(
                "RAW_FRAME_BINDING_MISMATCH",
                f"raw frame admission {frame_id!r} is stale",
            )
        if (
            admission["policy"]["transparent_rgb"] != quality_policy["transparent_rgb"]
            or admission["policy"]["minimum_margin"] != quality_policy["minimum_margin"]
        ):
            raise EvidenceError(
                "RAW_FRAME_BINDING_MISMATCH",
                f"raw frame admission {frame_id!r} does not bind the delivery quality policy",
            )
        source_path = manifest_path.parent / artifact["path"]
        try:
            with Image.open(source_path) as opened:
                if opened.mode != "RGBA":
                    raise EvidenceError(
                        "RAW_FRAME_BINDING_MISMATCH",
                        f"raw frame source {frame_id!r} is not RGBA",
                    )
                image = opened.copy()
        except EvidenceError:
            raise
        except (OSError, ValueError) as error:
            raise EvidenceError(
                "RAW_FRAME_BINDING_MISMATCH",
                f"raw frame source {frame_id!r} cannot be replayed",
            ) from error
        rgba = np.asarray(image, dtype=np.uint8)
        alpha = rgba[..., 3]
        visible = alpha > 0
        if not np.any(visible):
            raise EvidenceError(
                "RAW_FRAME_BINDING_MISMATCH",
                f"raw frame source {frame_id!r} is empty",
            )
        ys, xs = np.nonzero(visible)
        bounds = [
            int(xs.min()),
            int(ys.min()),
            int(xs.max()) + 1,
            int(ys.max()) + 1,
        ]
        margins = [
            bounds[0],
            bounds[1],
            image.width - bounds[2],
            image.height - bounds[3],
        ]
        alpha_total = float(alpha.sum())
        expected_alpha = {
            "nonzero_bounds": bounds,
            "margins": margins,
            "opaque_pixels": int(np.count_nonzero(alpha == 255)),
            "partial_alpha_pixels": int(np.count_nonzero((alpha > 0) & (alpha < 255))),
            "centroid": [
                round(float((xs * alpha[ys, xs]).sum()) / alpha_total, 6),
                round(float((ys * alpha[ys, xs]).sum()) / alpha_total, 6),
            ],
        }
        if any(admission["alpha"][key] != value for key, value in expected_alpha.items()):
            raise EvidenceError(
                "RAW_FRAME_MEASUREMENT_MISMATCH",
                f"raw frame admission {frame_id!r} measurements do not replay",
            )
        hidden_rgb = int(
            np.count_nonzero((alpha == 0) & np.any(rgba[..., :3] != 0, axis=2))
        )
        observed_hidden = admission["alpha"]["transparent_rgb_pixels_observed"]
        normalized = admission["policy"]["normalized"]
        if (
            hidden_rgb != 0
            or normalized
            or observed_hidden != 0
            or min(margins) < admission["policy"]["minimum_margin"]
            or admission["source"]["rgba_sha256"] != hashlib.sha256(image.tobytes()).hexdigest()
        ):
            raise EvidenceError(
                "RAW_FRAME_MEASUREMENT_MISMATCH",
                f"raw frame admission {frame_id!r} policy evidence does not replay",
            )


def _validate_diagnostics(
    diagnostics_path: Path,
    diagnostics: dict[str, Any],
    manifest_path: Path,
    manifest_hash: str,
    pipeline_path: Path,
    quality_policy: dict[str, Any],
) -> None:
    if diagnostics["package_manifest"]["sha256"] != manifest_hash:
        raise EvidenceError(
            "HASH_MISMATCH", "motion diagnostics does not bind the current package manifest"
        )
    resolve_job_reference(
        diagnostics_path.parent.resolve(),
        diagnostics["package_manifest"],
        "motion diagnostics package manifest",
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
    measured = recompute_motion_metrics(manifest_path, pipeline_path)
    if diagnostics["clips"] != measured:
        raise EvidenceError(
            "DIAGNOSTIC_MEASUREMENT_MISMATCH",
            "sealed diagnostic measurements do not replay from the package pixels",
        )
    maximum_step = quality_policy["maximum_alpha_centroid_step"]
    for clip in measured:
        centroids = [cell["alpha_centroid"] for cell in clip["cells"]]
        for index, (previous, current) in enumerate(zip(centroids, centroids[1:]), start=1):
            if previous is None or current is None:
                raise EvidenceError(
                    "QUALITY_GATE_FAILED",
                    f"clip {clip['clip_id']!r} contains an empty logical position",
                )
            step = max(abs(current[0] - previous[0]), abs(current[1] - previous[1]))
            if step > maximum_step:
                raise EvidenceError(
                    "QUALITY_GATE_FAILED",
                    f"clip {clip['clip_id']!r} alpha-centroid step at position {index} exceeds the configured limit",
                )


def _validate_review_coverage(
    review: dict[str, Any], expected_subjects: dict[str, str]
) -> None:
    actual_subjects = {
        subject["id"]: (subject["schema_version"], subject["sha256"])
        for subject in review["subjects"]
    }
    expected_with_schemas = {
        "identity": (IDENTITY_SCHEMA_V2, expected_subjects["identity"]),
        "motion-plan": (MOTION_PLAN_SCHEMA_V2, expected_subjects["motion-plan"]),
        "diagnostics": (DIAGNOSTICS_SCHEMA_V2, expected_subjects["diagnostics"]),
        "package": ("spritesheet-package/v5", expected_subjects["package"]),
    }
    if actual_subjects != expected_with_schemas:
        raise EvidenceError(
            "REVIEW_COVERAGE_MISMATCH",
            "review packet must exactly bind identity, motion plan, diagnostics, and package",
        )
    acceptable = [
        observation["subject_id"]
        for review_record in review["reviews"]
        for observation in review_record["observations"]
        if observation["disposition"] == "acceptable"
    ]
    if len(acceptable) != len(expected_subjects) or set(acceptable) != set(expected_subjects):
        raise EvidenceError(
            "REVIEW_COVERAGE_MISMATCH",
            "every v2 delivery review subject requires an acceptable observation",
        )


def _copy_document(
    document: dict[str, Any], target: Path, destination: Path, budget: BuildBudget
) -> None:
    budget.reserve(
        len(canonical_json_bytes(document)), target.relative_to(destination).as_posix()
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    write_canonical_json(target, document)


def seal_delivery_v2(
    request_path: Path, output_dir: Path, pipeline_path: Path
) -> None:
    from .delivery import _verify_package

    request = read_json(request_path, "delivery request")
    validate_delivery_v2(request, request=True)
    identity_path, identity_hash, identity = _load_ref(
        request["identity_bible"], "identity bible", IDENTITY_SCHEMA_V2
    )
    plan_path, plan_hash, motion_plan = _load_ref(
        request["motion_plan"], "motion plan", MOTION_PLAN_SCHEMA_V2
    )
    if identity["approval"]["status"] != "approved" or motion_plan["approval"]["status"] != "approved":
        raise EvidenceError(
            "APPROVAL_REQUIRED", "identity bible and complete motion plan must be approved"
        )
    if motion_plan["content"]["identity_bible_sha256"] != identity_hash:
        raise EvidenceError(
            "HASH_MISMATCH", "motion plan does not bind the current identity bible"
        )
    admission_inputs: list[tuple[Path, str, dict[str, Any]]] = []
    for index, reference in enumerate(request["raw_frame_admissions"]):
        admission_inputs.append(
            _load_ref(
                reference,
                f"raw frame admission[{index}]",
                RAW_FRAME_ADMISSION_SCHEMA,
            )
        )
    diagnostics_path, diagnostics_hash, diagnostics = _load_ref(
        request["motion_diagnostics"], "motion diagnostics", DIAGNOSTICS_SCHEMA_V2
    )
    review_path, review_hash, review = _load_ref(
        request["review_packet"], "review packet", REVIEW_SCHEMA
    )
    _verify_review_assets(review_path, review)
    if review["decision"]["status"] != "approved":
        raise EvidenceError("APPROVAL_REQUIRED", "review packet decision must be approved")
    manifest_path, manifest_hash = verify_file_reference(
        request["pixel_package"]["manifest"], "pixel package manifest"
    )
    if manifest_path.name != "manifest.json":
        raise EvidenceError("PACKAGE_INVALID", "pixel package manifest must be named manifest.json")
    _verify_package(manifest_path, pipeline_path)
    tree_hash = package_tree_sha256(manifest_path.parent)
    if request["pixel_package"]["package_tree_sha256"] != tree_hash:
        raise EvidenceError("HASH_MISMATCH", "pixel package tree hash does not match")
    manifest = read_json(manifest_path, "pixel package manifest")
    _validate_identity_binding(identity, manifest)
    _validate_plan_binding(motion_plan, manifest)
    _validate_raw_admissions(
        [item[2] for item in admission_inputs],
        motion_plan,
        plan_hash,
        manifest,
        manifest_path,
        request["quality_policy"],
    )
    _validate_diagnostics(
        diagnostics_path,
        diagnostics,
        manifest_path,
        manifest_hash,
        pipeline_path,
        request["quality_policy"],
    )
    expected_subjects = {
        "identity": identity_hash,
        "motion-plan": plan_hash,
        "diagnostics": diagnostics_hash,
        "package": manifest_hash,
    }
    _validate_review_coverage(review, expected_subjects)
    reject_path_overlap(
        output_dir,
        [
            request_path,
            manifest_path.parent,
            diagnostics_path.parent,
            review_path,
            identity_path,
            plan_path,
            *[item[0] for item in admission_inputs],
        ],
    )

    def build(destination: Path) -> None:
        budget = BuildBudget()

        def copy_file(source: Path, target: Path, digest: str) -> None:
            copy_bound_file(
                source,
                target,
                digest,
                budget=budget,
                budget_location=target.relative_to(destination).as_posix(),
            )

        package_destination = destination / "package"
        for source in inspect_tree(manifest_path.parent):
            copy_file(
                source,
                package_destination / source.relative_to(manifest_path.parent),
                sha256_file(source),
            )
        if package_tree_sha256(package_destination) != tree_hash:
            raise EvidenceError("COPY_VERIFY_FAILED", "copied package tree hash changed")
        evidence_root = destination / "evidence"
        identity_destination = evidence_root / "identity-bible.json"
        plan_destination = evidence_root / "motion-plan.json"
        _copy_document(identity, identity_destination, destination, budget)
        _copy_document(motion_plan, plan_destination, destination, budget)
        admission_refs: list[dict[str, str]] = []
        for index, (_, _, admission) in enumerate(admission_inputs):
            target = evidence_root / "raw-frame-admissions" / f"{index:04d}.json"
            _copy_document(admission, target, destination, budget)
            admission_refs.append(
                {
                    "ref": target.relative_to(destination).as_posix(),
                    "sha256": sha256_file(target),
                }
            )
        diagnostics_destination = evidence_root / "motion-diagnostics"
        diagnostics_document = diagnostics_destination / diagnostics_path.name
        copy_file(diagnostics_path, diagnostics_document, diagnostics_hash)
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
                diagnostics_path.parent.resolve(), reference, f"motion diagnostics.{location}"
            )
            copy_file(source, diagnostics_destination / reference["ref"], reference["sha256"])
        review_root = evidence_root / "review"
        for index, item in enumerate(review["evidence"]):
            source, _ = resolve_job_reference(
                review_path.parent.resolve(),
                {"ref": item["ref"], "sha256": item["sha256"]},
                f"review evidence[{index}]",
            )
            copy_file(source, review_root / item["ref"], item["sha256"])
        review_destination = review_root / "review-packet.json"
        _copy_document(review, review_destination, destination, budget)
        delivery = {
            "schema_version": DELIVERY_SCHEMA_V2,
            "job_id": request["job_id"],
            "status": "package-ready",
            "identity_bible": {
                "ref": identity_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(identity_destination),
            },
            "motion_plan": {
                "ref": plan_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(plan_destination),
            },
            "raw_frame_admissions": admission_refs,
            "pixel_package": {
                "manifest": {
                    "ref": "package/manifest.json",
                    "sha256": sha256_file(package_destination / "manifest.json"),
                },
                "package_tree_sha256": tree_hash,
            },
            "motion_diagnostics": {
                "ref": diagnostics_document.relative_to(destination).as_posix(),
                "sha256": sha256_file(diagnostics_document),
            },
            "review_packet": {
                "ref": review_destination.relative_to(destination).as_posix(),
                "sha256": sha256_file(review_destination),
            },
            "quality_policy": request["quality_policy"],
            "files": [
                {
                    "ref": path.relative_to(destination).as_posix(),
                    "sha256": sha256_file(path),
                }
                for path in inspect_tree(destination)
            ],
        }
        validate_document(delivery, DELIVERY_SCHEMA_V2)
        budget.reserve(len(canonical_json_bytes(delivery)), "delivery.json")
        delivery_path = destination / "delivery.json"
        write_canonical_json(delivery_path, delivery)
        report = verification_report_v2(delivery_path, pipeline_path)
        if not report["passed"]:
            error = report.get("error") or {}
            raise EvidenceError(
                "STAGING_VERIFY_FAILED",
                str(error.get("message", "staged delivery verification failed")),
            )

    atomic_directory(output_dir, build)


def verification_report_v2(
    delivery_path: Path, pipeline_path: Path
) -> dict[str, Any]:
    from .delivery import _verify_package

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
        validate_document(delivery, DELIVERY_SCHEMA_V2)
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
        if package_tree_sha256(manifest_path.parent) != delivery["pixel_package"]["package_tree_sha256"]:
            raise EvidenceError("HASH_MISMATCH", "sealed package tree hash does not match")
        manifest = read_json(manifest_path, "pixel package manifest")
        record(
            "MACHINE-VERIFIED",
            "pixel-package",
            "v5 replay, manifest hash, closed tree, rendering receipt, and assembly pass",
        )
        identity_path, identity_hash = resolve_job_reference(
            root, delivery["identity_bible"], "identity bible"
        )
        identity = read_json(identity_path, "identity bible")
        validate_document(identity, IDENTITY_SCHEMA_V2)
        plan_path, plan_hash = resolve_job_reference(root, delivery["motion_plan"], "motion plan")
        motion_plan = read_json(plan_path, "motion plan")
        validate_document(motion_plan, MOTION_PLAN_SCHEMA_V2)
        if identity["approval"]["status"] != "approved" or motion_plan["approval"]["status"] != "approved":
            raise EvidenceError("APPROVAL_REQUIRED", "identity and motion plan approvals are not current")
        if motion_plan["content"]["identity_bible_sha256"] != identity_hash:
            raise EvidenceError("HASH_MISMATCH", "motion plan identity binding is stale")
        _validate_identity_binding(identity, manifest)
        _validate_plan_binding(motion_plan, manifest)
        record(
            "REVIEWED",
            "identity-and-motion-plan",
            "approved identity and complete per-position plan are current and package-bound",
        )
        admission_documents: list[dict[str, Any]] = []
        for index, reference in enumerate(delivery["raw_frame_admissions"]):
            path, _ = resolve_job_reference(
                root, reference, f"raw frame admission[{index}]"
            )
            document = read_json(path, f"raw frame admission[{index}]")
            validate_document(document, RAW_FRAME_ADMISSION_SCHEMA)
            admission_documents.append(document)
        _validate_raw_admissions(
            admission_documents,
            motion_plan,
            plan_hash,
            manifest,
            manifest_path,
            delivery["quality_policy"],
        )
        record(
            "MACHINE-VERIFIED",
            "raw-frame-admission",
            "every concrete high-resolution source is plan-bound and policy-admitted exactly once",
        )
        diagnostics_path, diagnostics_hash = resolve_job_reference(
            root, delivery["motion_diagnostics"], "motion diagnostics"
        )
        diagnostics = read_json(diagnostics_path, "motion diagnostics")
        validate_document(diagnostics, DIAGNOSTICS_SCHEMA_V2)
        _validate_diagnostics(
            diagnostics_path,
            diagnostics,
            manifest_path,
            manifest_hash,
            pipeline_path,
            delivery["quality_policy"],
        )
        record(
            "MACHINE-VERIFIED",
            "motion-diagnostics",
            "all sealed motion measurements replay exactly from final sheet pixels",
        )
        review_path, review_hash = resolve_job_reference(
            root, delivery["review_packet"], "review packet"
        )
        review = read_json(review_path, "review packet")
        validate_document(review, REVIEW_SCHEMA)
        _verify_review_assets(review_path, review)
        if review["decision"]["status"] != "approved":
            raise EvidenceError("APPROVAL_REQUIRED", "review packet is not approved")
        _validate_review_coverage(
            review,
            {
                "identity": identity_hash,
                "motion-plan": plan_hash,
                "diagnostics": diagnostics_hash,
                "package": manifest_hash,
            },
        )
        record(
            "REVIEWED",
            "review-packet",
            "native-size and motion presentations have complete hash-bound acceptable observations",
        )
        semantic_files = {
            path.relative_to(root).as_posix() for path in inspect_tree(manifest_path.parent)
        }
        semantic_files.update(
            {
                delivery["identity_bible"]["ref"],
                delivery["motion_plan"]["ref"],
                delivery["motion_diagnostics"]["ref"],
                delivery["review_packet"]["ref"],
                *(item["ref"] for item in delivery["raw_frame_admissions"]),
            }
        )
        diagnostics_base = Path(delivery["motion_diagnostics"]["ref"]).parent
        semantic_files.add((diagnostics_base / diagnostics["package_manifest"]["ref"]).as_posix())
        semantic_files.update(
            (diagnostics_base / reference["ref"]).as_posix()
            for reference in diagnostics["assets"].values()
        )
        semantic_files.update(
            (diagnostics_base / preview["asset"]["ref"]).as_posix()
            for preview in diagnostics["previews"]
        )
        review_base = Path(delivery["review_packet"]["ref"]).parent
        semantic_files.update(
            (review_base / item["ref"]).as_posix() for item in review["evidence"]
        )
        if set(actual_files) != semantic_files:
            raise EvidenceError(
                "DELIVERY_TREE_MISMATCH",
                "delivery root contains files outside semantic evidence references",
            )
        record(
            "MACHINE-VERIFIED",
            "delivery-state",
            "the package-ready evidence closure is complete and replayable",
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
        code = failure.code if isinstance(failure, EvidenceError) else "VERIFICATION_FAILED"
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
        "schema_version": "spritesheet-delivery-verification-report/v2",
        "delivery": str(delivery_path),
        "passed": passed,
        "results": results,
        "error": error,
    }
