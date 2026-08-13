from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import test_spritesheet_pipeline as pipeline_tests
from production_evidence.io import (
    BuildBudget,
    canonical_sha256,
    copy_bound_file,
    package_tree_sha256,
    sha256_file,
    write_canonical_json,
)
from production_evidence.schemas import validate_delivery, validate_document

SCRIPT = SCRIPTS_DIR / "spritesheet_delivery.py"


class SpritesheetDeliveryTests(unittest.TestCase):
    @staticmethod
    def approval_hash(
        schema_version: str, id_key: str, subject_id: str, content: dict[str, object]
    ) -> str:
        return canonical_sha256(
            {"schema_version": schema_version, id_key: subject_id, "content": content}
        )

    @staticmethod
    def review_hash(
        packet_id: str,
        subjects: list[dict[str, object]],
        evidence: list[dict[str, object]],
        reviews: list[dict[str, object]],
    ) -> str:
        return canonical_sha256(
            {
                "schema_version": "review-packet/v1",
                "review_packet_id": packet_id,
                "subjects": subjects,
                "evidence": evidence,
                "reviews": reviews,
            }
        )

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_temporary = tempfile.TemporaryDirectory()
        cls.fixture_root = Path(cls.fixture_temporary.name)
        original_temporary_directory = tempfile.TemporaryDirectory

        class FixtureDirectory:
            def __enter__(self) -> str:
                return str(cls.fixture_root)

            def __exit__(self, *unused: object) -> None:
                return None

        tempfile.TemporaryDirectory = FixtureDirectory
        try:
            cls(
                methodName="test_diagnose_seal_and_verify_package_ready_delivery"
            ).test_diagnose_seal_and_verify_package_ready_delivery()
        finally:
            tempfile.TemporaryDirectory = original_temporary_directory
        cls.fixture_manifest = cls.fixture_root / "package" / "manifest.json"
        cls.fixture_delivery = cls.fixture_root / "sealed" / "delivery.json"
        cls.fixture_request = cls.fixture_root / "delivery-request.json"
        (cls.fixture_delivery.parent / "unlisted.txt").unlink()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_temporary.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def build_package(self, root: Path) -> Path:
        helper = pipeline_tests.SpritesheetPipelineTests(methodName="runTest")
        request_path, _ = helper.make_production_request(root)
        package = root / "package"
        built = helper.run_cli(
            "build-package",
            "--request",
            str(request_path),
            "--output-dir",
            str(package),
        )
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        return package / "manifest.json"

    @staticmethod
    def tree_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()
        }

    def copy_delivery_fixture(self, root: Path) -> Path:
        destination = root / "sealed"
        shutil.copytree(self.fixture_delivery.parent, destination)
        return destination / "delivery.json"

    @staticmethod
    def rewrite_declared_file(delivery_path: Path, relative_path: str) -> None:
        delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
        digest = sha256_file(delivery_path.parent / relative_path)
        for item in delivery["files"]:
            if item["ref"] == relative_path:
                item["sha256"] = digest
                break
        else:
            raise AssertionError(f"undeclared fixture path: {relative_path}")
        for field in ("identity_bible", "motion_diagnostics", "review_packet"):
            if delivery[field]["ref"] == relative_path:
                delivery[field]["sha256"] = digest
        for field in ("motion_blueprints", "spacing_plans"):
            for item in delivery[field]:
                if item["ref"] == relative_path:
                    item["sha256"] = digest
        write_canonical_json(delivery_path, delivery)

    @staticmethod
    def stage_paths(output_dir: Path) -> list[Path]:
        return list(output_dir.parent.glob(f".{output_dir.name}.stage-*"))

    def copy_request(self, root: Path) -> tuple[Path, dict[str, object]]:
        request = json.loads(self.fixture_request.read_text(encoding="utf-8"))
        request_path = root / "delivery-request.json"
        write_canonical_json(request_path, request)
        return request_path, request

    @staticmethod
    def copy_request_document(
        root: Path,
        request: dict[str, object],
        field: str,
        *,
        index: int | None = None,
    ) -> tuple[Path, dict[str, object]]:
        reference = request[field] if index is None else request[field][index]
        source = Path(reference["path"])
        document = json.loads(source.read_text(encoding="utf-8"))
        destination = root / source.name
        write_canonical_json(destination, document)
        reference["path"] = str(destination)
        reference["sha256"] = sha256_file(destination)
        return destination, document

    def test_help_lists_delivery_commands_and_schemas(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("diagnose", result.stdout)
        self.assertIn("seal-delivery", result.stdout)
        self.assertIn("runtime-playback-proof/v1", result.stdout)

    def test_identity_schema_is_closed_and_hash_bound(self) -> None:
        content = {
            "subject": "actor",
            "canonical_bindings": [],
            "invariants": [],
            "allowed_variations": [],
            "forbidden_drifts": [],
        }
        identity = {
            "schema_version": "identity-bible/v1",
            "identity_id": "actor-v1",
            "content": content,
            "approval": {
                "status": "approved",
                "subject_sha256": self.approval_hash(
                    "identity-bible/v1", "identity_id", "actor-v1", content
                ),
                "reviewer": "reviewer@example.com",
                "evidence": "approved identity board",
            },
        }
        validate_document(identity)
        identity["unsupported"] = True
        with self.assertRaisesRegex(Exception, "fields must be exactly"):
            validate_document(identity)

    def test_motion_blueprint_rejects_empty_action_evidence(self) -> None:
        request = json.loads(self.fixture_request.read_text(encoding="utf-8"))
        blueprint_path = Path(request["motion_blueprints"][0]["path"])
        blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
        blueprint["content"]["action_evidence"] = []
        blueprint["approval"]["subject_sha256"] = self.approval_hash(
            "motion-blueprint/v1",
            "blueprint_id",
            blueprint["blueprint_id"],
            blueprint["content"],
        )
        with self.assertRaisesRegex(Exception, "action_evidence must be non-empty"):
            validate_document(blueprint)

    def test_runtime_verified_rejects_null_proof(self) -> None:
        digest = "0" * 64
        request = {
            "schema_version": "spritesheet-production-delivery/v1",
            "job_id": "job",
            "status": "runtime-verified",
            "identity_bible": {"path": "/identity.json", "sha256": digest},
            "motion_blueprints": [],
            "spacing_plans": [],
            "pixel_package": {
                "manifest": {"path": "/manifest.json", "sha256": digest},
                "package_tree_sha256": digest,
            },
            "motion_diagnostics": {"path": "/diagnostics.json", "sha256": digest},
            "review_packet": {"path": "/review.json", "sha256": digest},
            "runtime": {
                "scope": "required",
                "contract": {"path": "/runtime-contract.json", "sha256": digest},
                "projection": {"path": "/runtime-projection.json", "sha256": digest},
                "proof": None,
            },
        }
        with self.assertRaisesRegex(Exception, "runtime playback proof"):
            validate_delivery(request, request=True)

    def test_runtime_proof_rejects_nonfinite_device_pixel_ratio(self) -> None:
        proof = {
            "schema_version": "runtime-playback-proof/v1",
            "proof_id": "proof",
            "package_manifest_sha256": "0" * 64,
            "runtime_contract_sha256": "1" * 64,
            "entry_point": "runtime",
            "viewport": {"width": 1, "height": 1, "device_pixel_ratio": float("inf")},
            "playback": {
                "clip_ids": ["clip"],
                "timing_source": "manifest",
                "loop_count": 1,
            },
            "events": [],
            "rendering": {
                "scale_mode": "nearest",
                "alpha_mode": "straight",
                "checks_passed": True,
                "observations": [],
            },
            "evidence": [
                {"kind": "runtime-capture", "ref": "capture.bin", "sha256": "2" * 64}
            ],
            "supplied_by": "tester",
        }
        with self.assertRaisesRegex(Exception, "device_pixel_ratio"):
            validate_document(proof)

    def test_build_budget_counts_hardlinks_and_repeated_targets_separately(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            hardlink = root / "hardlink.bin"
            source.write_bytes(b"12345678")
            os.link(source, hardlink)
            budget = BuildBudget(max_files=3, max_bytes=20)
            budget.reserve_file(source, "review/evidence-0.bin")
            budget.reserve_file(hardlink, "review/evidence-1.bin")
            with self.assertRaisesRegex(Exception, "build budget exceeded"):
                budget.reserve_file(source, "runtime/evidence-0.bin")

    def test_build_budget_counts_review_and_runtime_attachments_before_write(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attachment = root / "shared-capture.bin"
            attachment.write_bytes(b"x" * 12)
            budget = BuildBudget(max_files=2, max_bytes=23)
            budget.reserve_file(attachment, "evidence/review/shared-capture.bin")
            with self.assertRaisesRegex(
                Exception, "runtime/evidence/shared-capture.bin"
            ):
                budget.reserve_file(attachment, "runtime/evidence/shared-capture.bin")

    def test_bound_copy_reserves_current_descriptor_size_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "attachment.bin"
            destination = root / "staged.bin"
            source.write_bytes(b"tiny")
            source.write_bytes(b"expanded")
            budget = BuildBudget(max_files=1, max_bytes=7)
            with self.assertRaisesRegex(Exception, "build budget exceeded"):
                copy_bound_file(
                    source,
                    destination,
                    sha256_file(source),
                    budget=budget,
                    budget_location="review/attachment.bin",
                )
            self.assertFalse(destination.exists())

    def test_delivery_package_copy_does_not_use_copytree(self) -> None:
        delivery_source = (
            TESTS_DIR.parent / "scripts" / "production_evidence" / "delivery.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("copytree", delivery_source)

    def test_verify_emits_structured_failure_for_missing_delivery(self) -> None:
        result = self.run_cli(
            "verify", "--delivery", "/definitely/missing/delivery.json"
        )
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["passed"])
        self.assertEqual(report["results"][0]["classification"], "MACHINE-VERIFIED")
        self.assertEqual(report["error"]["code"], "FILE_NOT_FOUND")

    def test_diagnose_rejects_package_overlap_without_changing_package_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            shutil.copytree(self.fixture_manifest.parent, package)
            manifest = package / "manifest.json"
            before = self.tree_bytes(package)
            result = self.run_cli(
                "diagnose",
                "--manifest",
                str(manifest),
                "--output-dir",
                str(package / "diagnostics"),
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "PATH_OVERLAP")
            self.assertEqual(self.tree_bytes(package), before)
            self.assertEqual(self.stage_paths(package / "diagnostics"), [])

    def test_seal_rejects_escaping_review_evidence_without_partial_output(self) -> None:
        for escaped_ref in ("../outside.bin", "/definitely/outside.bin"):
            with (
                self.subTest(ref=escaped_ref),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                request_path, request = self.copy_request(root)
                review_path, review = self.copy_request_document(
                    root, request, "review_packet"
                )
                outside = root / "outside.bin"
                outside.write_bytes(b"outside sentinel")
                review["evidence"][0]["ref"] = escaped_ref
                review["decision"]["subject_sha256"] = self.review_hash(
                    review["review_packet_id"],
                    review["subjects"],
                    review["evidence"],
                    review["reviews"],
                )
                write_canonical_json(review_path, review)
                request["review_packet"]["sha256"] = sha256_file(review_path)
                write_canonical_json(request_path, request)
                output = root / "sealed"
                result = self.run_cli(
                    "seal-delivery",
                    "--request",
                    str(request_path),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(
                    json.loads(result.stdout)["error"]["code"], "PATH_ESCAPE"
                )
                self.assertEqual(outside.read_bytes(), b"outside sentinel")
                self.assertFalse(output.exists())
                self.assertEqual(self.stage_paths(output), [])

    def test_verify_rejects_undeclared_file_and_missing_diagnostics_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            delivery_path = self.copy_delivery_fixture(root)
            extra = delivery_path.parent / "undeclared.bin"
            extra.write_bytes(b"undeclared")
            result = self.run_cli("verify", "--delivery", str(delivery_path))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["error"]["code"], "DELIVERY_TREE_MISMATCH"
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            delivery_path = self.copy_delivery_fixture(root)
            (
                delivery_path.parent
                / "evidence"
                / "motion-diagnostics"
                / "source"
                / "manifest.json"
            ).unlink()
            result = self.run_cli("verify", "--delivery", str(delivery_path))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["error"]["code"], "DELIVERY_TREE_MISMATCH"
            )

    def test_verify_rejects_tampered_review_observation_decision_and_evidence_hash(
        self,
    ) -> None:
        for tamper in ("observation", "decision", "evidence-hash"):
            with (
                self.subTest(tamper=tamper),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                delivery_path = self.copy_delivery_fixture(root)
                delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
                review_ref = delivery["review_packet"]["ref"]
                review_path = delivery_path.parent / review_ref
                review = json.loads(review_path.read_text(encoding="utf-8"))
                if tamper == "observation":
                    review["reviews"][0]["observations"][0]["statement"] += " tampered"
                elif tamper == "decision":
                    review["decision"]["subject_sha256"] = "0" * 64
                else:
                    review["evidence"][0]["sha256"] = "0" * 64
                    review["decision"]["subject_sha256"] = self.review_hash(
                        review["review_packet_id"],
                        review["subjects"],
                        review["evidence"],
                        review["reviews"],
                    )
                write_canonical_json(review_path, review)
                self.rewrite_declared_file(delivery_path, review_ref)
                result = self.run_cli("verify", "--delivery", str(delivery_path))
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(
                    json.loads(result.stdout)["error"]["code"],
                    {"APPROVAL_HASH_MISMATCH", "HASH_MISMATCH"},
                )

    def test_rejected_approvals_and_nonacceptable_review_cannot_be_sealed(self) -> None:
        cases = (
            ("identity_bible", None, "approval", "rejected"),
            ("motion_blueprints", 0, "approval", "rejected"),
            ("spacing_plans", 0, "approval", "rejected"),
            ("review_packet", None, "review", "uncertain"),
            ("review_packet", None, "review", "rework-required"),
        )
        for field, index, kind, value in cases:
            with (
                self.subTest(field=field, value=value),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                request_path, request = self.copy_request(root)
                document_path, document = self.copy_request_document(
                    root, request, field, index=index
                )
                if kind == "approval":
                    document["approval"]["status"] = value
                else:
                    document["reviews"][0]["observations"][0]["disposition"] = value
                    document["decision"]["subject_sha256"] = self.review_hash(
                        document["review_packet_id"],
                        document["subjects"],
                        document["evidence"],
                        document["reviews"],
                    )
                write_canonical_json(document_path, document)
                reference = request[field] if index is None else request[field][index]
                reference["sha256"] = sha256_file(document_path)
                write_canonical_json(request_path, request)
                output = root / "sealed"
                result = self.run_cli(
                    "seal-delivery",
                    "--request",
                    str(request_path),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(
                    json.loads(result.stdout)["error"]["code"], "APPROVAL_REQUIRED"
                )
                self.assertFalse(output.exists())

    def test_runtime_verified_rejects_invalid_scope_and_stale_projection_binding(
        self,
    ) -> None:
        request = json.loads(self.fixture_request.read_text(encoding="utf-8"))
        request["status"] = "runtime-verified"
        with self.assertRaisesRegex(Exception, "runtime scope must be required"):
            validate_delivery(request, request=True)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path, request = self.copy_request(root)
            manifest_hash = request["pixel_package"]["manifest"]["sha256"]
            contract = root / "runtime-contract.json"
            projection = root / "runtime-projection.json"
            capture = root / "runtime-capture.png"
            proof = root / "runtime-proof.json"
            contract.write_text("{}", encoding="utf-8")
            manifest = json.loads(
                Path(request["pixel_package"]["manifest"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            manifest_contract = manifest["contract"]
            projection_document = {
                "schema_version": "spritesheet-runtime-projection/v1",
                "package_manifest_sha256": "0" * 64,
                "runtime_contract_sha256": sha256_file(contract),
                "contract": {
                    key: manifest_contract[key]
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
            write_canonical_json(projection, projection_document)
            capture.write_bytes(b"runtime capture")
            proof_document = {
                "schema_version": "runtime-playback-proof/v1",
                "proof_id": "runtime-proof-v1",
                "package_manifest_sha256": manifest_hash,
                "runtime_contract_sha256": sha256_file(contract),
                "entry_point": "test",
                "viewport": {"width": 320, "height": 180, "device_pixel_ratio": 1},
                "playback": {
                    "clip_ids": ["walk-east"],
                    "timing_source": "manifest",
                    "loop_count": 1,
                },
                "events": [],
                "rendering": {
                    "scale_mode": "nearest",
                    "alpha_mode": "straight",
                    "checks_passed": True,
                    "observations": ["rendered"],
                },
                "evidence": [
                    {
                        "kind": "runtime-capture",
                        "ref": capture.name,
                        "sha256": sha256_file(capture),
                    }
                ],
                "supplied_by": "tester",
            }
            write_canonical_json(proof, proof_document)
            request["status"] = "runtime-verified"
            request["runtime"] = {
                "scope": "required",
                "contract": {"path": str(contract), "sha256": sha256_file(contract)},
                "projection": {
                    "path": str(projection),
                    "sha256": sha256_file(projection),
                },
                "proof": {"path": str(proof), "sha256": sha256_file(proof)},
            }
            write_canonical_json(request_path, request)
            output = root / "sealed"
            result = self.run_cli(
                "seal-delivery",
                "--request",
                str(request_path),
                "--output-dir",
                str(output),
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["error"]["code"],
                "RUNTIME_BINDING_MISMATCH",
            )
            self.assertFalse(output.exists())

    def test_runtime_metadata_and_runtime_verified_happy_paths(self) -> None:
        manifest = json.loads(self.fixture_manifest.read_text(encoding="utf-8"))
        manifest_hash = sha256_file(self.fixture_manifest)
        for status in ("runtime-metadata-complete", "runtime-verified"):
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                request_path, request = self.copy_request(root)
                contract_path = root / "runtime-contract.json"
                contract_path.write_text("opaque runtime contract", encoding="utf-8")
                contract_hash = sha256_file(contract_path)
                projection = {
                    "schema_version": "spritesheet-runtime-projection/v1",
                    "package_manifest_sha256": manifest_hash,
                    "runtime_contract_sha256": contract_hash,
                    "contract": {
                        key: manifest["contract"][key]
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
                projection_path = root / "runtime-projection.json"
                write_canonical_json(projection_path, projection)
                proof_reference = None
                if status == "runtime-verified":
                    capture_path = root / "runtime-capture.bin"
                    capture_path.write_bytes(b"runtime capture")
                    proof = {
                        "schema_version": "runtime-playback-proof/v1",
                        "proof_id": "runtime-proof-v1",
                        "package_manifest_sha256": manifest_hash,
                        "runtime_contract_sha256": contract_hash,
                        "entry_point": "test-runtime",
                        "viewport": {
                            "width": 320,
                            "height": 180,
                            "device_pixel_ratio": 1.0,
                        },
                        "playback": {
                            "clip_ids": [clip["id"] for clip in manifest["clips"]],
                            "timing_source": "manifest",
                            "loop_count": 1,
                        },
                        "events": [
                            {
                                "name": event["name"],
                                "clip_id": clip["id"],
                                "position": event["position"],
                                "observed": True,
                            }
                            for clip in manifest["clips"]
                            for event in clip["events"]
                        ],
                        "rendering": {
                            "scale_mode": "nearest",
                            "alpha_mode": "straight",
                            "checks_passed": True,
                            "observations": ["verified"],
                        },
                        "evidence": [
                            {
                                "kind": "runtime-capture",
                                "ref": capture_path.name,
                                "sha256": sha256_file(capture_path),
                            }
                        ],
                        "supplied_by": "tester",
                    }
                    proof_path = root / "runtime-proof.json"
                    write_canonical_json(proof_path, proof)
                    proof_reference = {
                        "path": str(proof_path),
                        "sha256": sha256_file(proof_path),
                    }
                request["status"] = status
                request["runtime"] = {
                    "scope": "required",
                    "contract": {"path": str(contract_path), "sha256": contract_hash},
                    "projection": {
                        "path": str(projection_path),
                        "sha256": sha256_file(projection_path),
                    },
                    "proof": proof_reference,
                }
                write_canonical_json(request_path, request)
                output = root / "sealed"
                sealed = self.run_cli(
                    "seal-delivery",
                    "--request",
                    str(request_path),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(sealed.returncode, 0, sealed.stdout + sealed.stderr)
                verified = self.run_cli(
                    "verify", "--delivery", str(output / "delivery.json")
                )
                self.assertEqual(
                    verified.returncode, 0, verified.stdout + verified.stderr
                )
                self.assertTrue(json.loads(verified.stdout)["passed"])

    def test_diagnose_rejects_symlink_and_fifo_manifest_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.subTest(kind="symlink"):
                symlink = root / "manifest.json"
                symlink.symlink_to(self.fixture_manifest)
                output = root / "symlink-output"
                result = self.run_cli(
                    "diagnose", "--manifest", str(symlink), "--output-dir", str(output)
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(
                    json.loads(result.stdout)["error"]["code"], "SYMLINK_FORBIDDEN"
                )
                self.assertFalse(output.exists())

            with self.subTest(kind="fifo"):
                fifo = root / "fifo-manifest.json"
                os.mkfifo(fifo)
                fifo_output = root / "fifo-output"
                result = self.run_cli(
                    "diagnose",
                    "--manifest",
                    str(fifo),
                    "--output-dir",
                    str(fifo_output),
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(
                    json.loads(result.stdout)["error"]["code"],
                    {"FILE_NOT_FOUND", "FILE_NOT_REGULAR", "RESOURCE_LIMIT"},
                )
                self.assertFalse(fifo_output.exists())

    def test_diagnose_is_byte_deterministic_across_distinct_output_directories(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "diagnostics-a"
            second = root / "diagnostics-b"
            for output in (first, second):
                result = self.run_cli(
                    "diagnose",
                    "--manifest",
                    str(self.fixture_manifest),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.tree_bytes(first), self.tree_bytes(second))

    def test_failed_diagnose_preserves_existing_output_and_leaves_no_stage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "diagnostics"
            output.mkdir()
            sentinel = output / "sentinel.txt"
            sentinel.write_bytes(b"preserve me")
            before = self.tree_bytes(output)
            result = self.run_cli(
                "diagnose",
                "--manifest",
                str(self.fixture_manifest),
                "--output-dir",
                str(output),
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(self.tree_bytes(output), before)
            self.assertEqual(self.stage_paths(output), [])

    def test_diagnose_seal_and_verify_package_ready_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.build_package(root)
            diagnostics_dir = root / "diagnostics"
            diagnosed = self.run_cli(
                "diagnose",
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(diagnostics_dir),
            )
            self.assertEqual(
                diagnosed.returncode, 0, diagnosed.stdout + diagnosed.stderr
            )
            diagnostics_path = diagnostics_dir / "motion-diagnostics.json"
            diagnostics_text = diagnostics_path.read_text(encoding="utf-8")
            diagnostics = json.loads(diagnostics_text)
            self.assertNotIn("center_of_mass", diagnostics_text)
            self.assertEqual(
                diagnostics["clips"][0]["cells"][0]["alpha_area"] > 0, True
            )
            self.assertIsNone(
                diagnostics["clips"][0]["cells"][0]["pixel_diff_from_previous"]
            )
            for name in (
                "contact-sheet.png",
                "native-size-board.png",
                "onion-skin.png",
                "previews/0000.gif",
            ):
                self.assertTrue((diagnostics_dir / name).is_file())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            clip = manifest["clips"][0]
            canonical_artifact = next(
                artifact
                for artifact in manifest["artifacts"]
                if artifact["id"] == clip["canonical_reference"]
            )
            canonical_admission = next(
                admission
                for admission in manifest["canonical_admissions"]
                if admission["canonical_reference"] == clip["canonical_reference"]
            )
            identity_content = {
                "subject": "test actor",
                "canonical_bindings": [
                    {
                        "canonical_id": clip["canonical_reference"],
                        "direction": clip["direction"],
                        "camera": clip["camera"],
                        "candidate_sha256": canonical_artifact["sha256"],
                        "admission_proof_sha256": canonical_admission["proof_sha256"],
                    }
                ],
                "invariants": [],
                "allowed_variations": [],
                "forbidden_drifts": [],
            }
            identity = {
                "schema_version": "identity-bible/v1",
                "identity_id": "test-actor-v1",
                "content": identity_content,
                "approval": {
                    "status": "approved",
                    "subject_sha256": self.approval_hash(
                        "identity-bible/v1",
                        "identity_id",
                        "test-actor-v1",
                        identity_content,
                    ),
                    "reviewer": "reviewer@example.com",
                    "evidence": "identity review",
                },
            }
            identity_path = root / "identity.json"
            write_canonical_json(identity_path, identity)
            position_count = len(clip["durations_ms"])
            blueprint_content = {
                "identity_bible_sha256": sha256_file(identity_path),
                "clip_id": clip["id"],
                "canonical_id": clip["canonical_reference"],
                "intent": "test action",
                "direction": clip["direction"],
                "camera": clip["camera"],
                "entry": "ready",
                "exit": "ready",
                "loop": clip["loop"],
                "root_motion": clip["root_motion"],
                "action_evidence": [
                    {
                        "evidence_id": "written-action-intent",
                        "ref": "test action",
                        "relationship": "written-intent",
                    }
                ],
                "positions": [
                    {
                        "frame_id": manifest["assembly"]["cells"][index]["source"],
                        "index": index,
                        "role": "keyframe"
                        if index in (0, position_count - 1)
                        else "in-between",
                        "phase": "test",
                        "action_beat": "test beat",
                        "purpose": "test purpose",
                        "pose": "test pose",
                        "orientation": "east",
                        "projection": "side",
                        "depth_and_occlusion": "declared",
                        "root_and_alpha_centroid_intent": "declared",
                        "contacts": [],
                        "transition_from_previous": "declared",
                        "transition_to_next": "declared",
                        "duration_ms": clip["durations_ms"][index],
                        "events": [
                            event["name"]
                            for event in clip["events"]
                            if event["position"] == index
                        ],
                        "previous_keyframe": None,
                        "next_keyframe": None,
                    }
                    for index in (0, position_count - 1)
                ],
            }
            blueprint = {
                "schema_version": "motion-blueprint/v1",
                "blueprint_id": "action-east-v1",
                "content": blueprint_content,
                "approval": {
                    "status": "approved",
                    "subject_sha256": self.approval_hash(
                        "motion-blueprint/v1",
                        "blueprint_id",
                        "action-east-v1",
                        blueprint_content,
                    ),
                    "reviewer": "reviewer@example.com",
                    "evidence": "motion blueprint review",
                },
            }
            blueprint_path = root / "blueprint.json"
            write_canonical_json(blueprint_path, blueprint)
            spacing_content = {
                "motion_blueprint_sha256": sha256_file(blueprint_path),
                "clip_id": clip["id"],
                "approved_keyframes": [
                    {
                        "frame_id": frame_id,
                        "source_sha256": next(
                            artifact["sha256"]
                            for artifact in manifest["artifacts"]
                            if artifact["id"] == frame_id
                        ),
                    }
                    for frame_id in (clip["frame_ids"][0], clip["frame_ids"][-1])
                ],
                "positions": [
                    {
                        "frame_id": manifest["assembly"]["cells"][index]["source"],
                        "index": index,
                        "role": "keyframe"
                        if index in (0, position_count - 1)
                        else "in-between",
                        "previous_keyframe": None,
                        "next_keyframe": None,
                        "duration_ms": clip["durations_ms"][index],
                        "events": [
                            event["name"]
                            for event in clip["events"]
                            if event["position"] == index
                        ],
                        "spacing": "declared spacing",
                        "arc": "declared arc",
                        "contacts": [],
                        "transition_from_previous": "declared",
                        "transition_to_next": "declared",
                    }
                    for index in range(position_count)
                ],
            }
            spacing = {
                "schema_version": "spacing-plan/v1",
                "spacing_plan_id": "action-east-spacing-v1",
                "content": spacing_content,
                "approval": {
                    "status": "approved",
                    "subject_sha256": self.approval_hash(
                        "spacing-plan/v1",
                        "spacing_plan_id",
                        "action-east-spacing-v1",
                        spacing_content,
                    ),
                    "reviewer": "reviewer@example.com",
                    "evidence": "spacing review",
                },
            }
            spacing_path = root / "spacing.json"
            write_canonical_json(spacing_path, spacing)
            subjects = [
                {
                    "id": "identity",
                    "schema_version": "identity-bible/v1",
                    "sha256": sha256_file(identity_path),
                },
                {
                    "id": "blueprint",
                    "schema_version": "motion-blueprint/v1",
                    "sha256": sha256_file(blueprint_path),
                },
                {
                    "id": "spacing",
                    "schema_version": "spacing-plan/v1",
                    "sha256": sha256_file(spacing_path),
                },
                {
                    "id": "diagnostics",
                    "schema_version": "motion-diagnostics/v1",
                    "sha256": sha256_file(diagnostics_path),
                },
                {
                    "id": "package",
                    "schema_version": "spritesheet-package/v4",
                    "sha256": sha256_file(manifest_path),
                },
            ]
            evidence = [
                {
                    "id": "contact-sheet",
                    "kind": "contact-sheet",
                    "ref": "diagnostics/contact-sheet.png",
                    "sha256": sha256_file(diagnostics_dir / "contact-sheet.png"),
                }
            ]
            reviews = [
                {
                    "reviewer": "reviewer@example.com",
                    "evidence_ids": ["contact-sheet"],
                    "observations": [
                        {
                            "subject_id": subject["id"],
                            "classification": "reviewed",
                            "disposition": "acceptable",
                            "statement": "Native-size and sequence presentation reviewed",
                        }
                        for subject in subjects
                    ],
                }
            ]
            review = {
                "schema_version": "review-packet/v1",
                "review_packet_id": "review-v1",
                "subjects": subjects,
                "evidence": evidence,
                "reviews": reviews,
                "decision": {
                    "status": "approved",
                    "subject_sha256": self.review_hash(
                        "review-v1", subjects, evidence, reviews
                    ),
                    "reviewer": "reviewer@example.com",
                    "evidence": "package accepted",
                },
            }
            review_path = root / "review.json"
            write_canonical_json(review_path, review)
            request = {
                "schema_version": "spritesheet-production-delivery/v1",
                "job_id": "test-job",
                "status": "package-ready",
                "identity_bible": {
                    "path": str(identity_path),
                    "sha256": sha256_file(identity_path),
                },
                "motion_blueprints": [
                    {"path": str(blueprint_path), "sha256": sha256_file(blueprint_path)}
                ],
                "spacing_plans": [
                    {"path": str(spacing_path), "sha256": sha256_file(spacing_path)}
                ],
                "pixel_package": {
                    "manifest": {
                        "path": str(manifest_path),
                        "sha256": sha256_file(manifest_path),
                    },
                    "package_tree_sha256": package_tree_sha256(manifest_path.parent),
                },
                "motion_diagnostics": {
                    "path": str(diagnostics_path),
                    "sha256": sha256_file(diagnostics_path),
                },
                "review_packet": {
                    "path": str(review_path),
                    "sha256": sha256_file(review_path),
                },
                "runtime": {
                    "scope": "not-requested",
                    "contract": None,
                    "projection": None,
                    "proof": None,
                },
            }
            request_path = root / "delivery-request.json"
            write_canonical_json(request_path, request)
            sealed_dir = root / "sealed"
            sealed = self.run_cli(
                "seal-delivery",
                "--request",
                str(request_path),
                "--output-dir",
                str(sealed_dir),
            )
            self.assertEqual(sealed.returncode, 0, sealed.stdout + sealed.stderr)
            verified = self.run_cli(
                "verify", "--delivery", str(sealed_dir / "delivery.json")
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            report = json.loads(verified.stdout)
            self.assertTrue(report["passed"])
            classifications = {result["classification"] for result in report["results"]}
            self.assertEqual(
                classifications,
                {"MACHINE-VERIFIED", "REVIEWED", "DECLARED", "SUPPLIED"},
            )
            extra = sealed_dir / "unlisted.txt"
            extra.write_text("unlisted", encoding="utf-8")
            rejected_extra = self.run_cli(
                "verify", "--delivery", str(sealed_dir / "delivery.json")
            )
            self.assertEqual(rejected_extra.returncode, 1)
            self.assertEqual(
                json.loads(rejected_extra.stdout)["error"]["code"],
                "DELIVERY_TREE_MISMATCH",
            )


if __name__ == "__main__":
    unittest.main()
