from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

TESTS_DIR = Path(__file__).parent
sys.path.insert(0, str(TESTS_DIR))

import test_spritesheet_pipeline as pipeline_tests

SCRIPT = Path(__file__).parents[1] / "scripts" / "spritesheet_production.py"


class SpritesheetProductionTests(unittest.TestCase):
    def run_cli(self, *arguments: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment.update(extra_env or {})
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments], check=False,
            capture_output=True, text=True, env=environment,
        )

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def write_rgba(path: Path, seed: int, size: tuple[int, int] = (400, 400)) -> None:
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, size[0] - 41, size[1] - 41), fill=(seed, 80, 160, 255))
        draw.rectangle((90, 60, 150, 130), fill=(255, seed, 20, 200))
        image.save(path)

    @staticmethod
    def tree_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()
        }

    def intent(self, root: Path, profile: str = "smooth-raster/v1") -> dict[str, object]:
        source = root / "identity.png"
        self.write_rgba(source, 30)
        return {
            "schema_version": "spritesheet-production-intent/v1",
            "base_revision": None,
            "mode": "create",
            "identity": {
                "sources": [{"id": "hero", "path": str(source)}],
                "declarations": {
                    "subject": "hero", "art_direction": "clean painted animation",
                    "camera": "orthographic-side", "direction": "east",
                    "recognition_constraints": ["retain the red head mark"],
                    "allowed_variations": ["limb articulation"],
                    "forbidden_drifts": ["costume replacement"],
                },
            },
            "clips": [{
                "id": "walk-east", "identity_source": "hero", "direction": "east",
                "camera": "orthographic-side", "loop": False, "root_motion": "in-place",
                "transition": "ready", "terminal_hold": True,
                "action_evidence": [{"evidence_id": "written-brief", "ref": "user authorizes motion design from the written intent", "relationship": "written-intent"}],
                "durations_ms": [100, 100], "events": [],
                "positions": [
                    {"id": "k0", "role": "keyframe", "phase": "contact"},
                    {"id": "k3", "role": "keyframe", "phase": "contact-opposite"},
                ],
            }],
            "target": {
                "frame_width": 32, "frame_height": 32, "animation_origin": [0, 0],
                "anchor": [16, 31], "safe_bounds": [2, 2, 30, 30],
            },
            "rendering_profile": {"id": profile, "outline": {"enabled": False, "target_width": "none"}},
            "output_scope": {},
            "runtime_scope": None,
        }

    def alpha_intent(self, root: Path, *, detached_fringe: bool) -> dict[str, object]:
        intent = self.intent(root)
        source = Path(intent["identity"]["sources"][0]["path"])
        image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if detached_fringe:
            draw.rectangle((96, 96, 415, 415), outline=(255, 255, 255, 32), width=2)
            draw.rectangle((160, 160, 351, 351), fill=(30, 80, 160, 255))
        else:
            draw.rectangle((127, 127, 384, 384), outline=(245, 245, 245, 8), width=2)
            draw.rectangle((129, 129, 382, 382), fill=(30, 80, 160, 255))
        image.save(source)
        intent["target"] = {
            "frame_width": 128,
            "frame_height": 128,
            "animation_origin": [0, 0],
            "anchor": [64, 127],
            "safe_bounds": [4, 4, 124, 124],
        }
        intent["rendering_profile"]["outline"] = {
            "enabled": True,
            "target_width": 2,
            "color": [7, 8, 9, 255],
        }
        return intent

    def test_help_exposes_only_advance_and_verify(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("{advance,verify}", result.stdout)

    def test_canonical_review_binds_alpha_policy_and_complete_preview_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.alpha_intent(root, detached_fringe=False))

            result = self.run_cli(
                "advance",
                "--job",
                str(root / "job"),
                "--intent",
                str(intent_path),
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads(result.stdout)["result"]["state"]
            self.assertEqual(state["phase"], "awaiting-canonical-review")
            records = state["outputs"]["canonical_references"]
            self.assertEqual(len(records), 1)
            evidence = json.loads(Path(records[0]["evidence_path"]).read_text(encoding="utf-8"))
            self.assertEqual(evidence["alpha_policy"]["status"], "passed")
            previews = [
                subject
                for subject in state["checkpoint"]["presentation"]["subjects"]
                if subject["kind"] == "canonical-review-preview"
            ]
            self.assertEqual(len(previews), 6)
            self.assertEqual(
                {(item["scale"], item["background"]) for item in previews},
                {
                    ("high-resolution", "white"),
                    ("high-resolution", "dark"),
                    ("high-resolution", "checkerboard"),
                    ("native", "white"),
                    ("native", "dark"),
                    ("native", "checkerboard"),
                },
            )
            for preview in previews:
                path = Path(preview["path"])
                self.assertTrue(path.is_file())
                self.assertEqual(preview["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_unbacked_low_alpha_fringe_never_opens_canonical_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            job = root / "job"
            self.write_json(intent_path, self.alpha_intent(root, detached_fringe=True))

            result = self.run_cli(
                "advance",
                "--job",
                str(job),
                "--intent",
                str(intent_path),
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["error"]["code"], "CANONICAL_ALPHA_GATE_FAILED")
            self.assertFalse((job / "state.json").exists())
            self.assertEqual(list(job.rglob("canonical-admission-proof.json")) if job.exists() else [], [])

    def test_nonopaque_outline_color_is_rejected_at_the_public_intent_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            job = root / "job"
            intent = self.alpha_intent(root, detached_fringe=False)
            intent["rendering_profile"]["outline"]["color"][3] = 254
            self.write_json(intent_path, intent)

            result = self.run_cli(
                "advance",
                "--job",
                str(job),
                "--intent",
                str(intent_path),
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["error"]["code"], "INVALID_CONTRACT")
            self.assertIn("color alpha must be 255", payload["error"]["message"])
            self.assertFalse(job.exists())

    def test_missing_opaque_silhouette_seed_is_a_typed_alpha_gate_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            job = root / "job"
            intent = self.alpha_intent(root, detached_fringe=False)
            source = Path(intent["identity"]["sources"][0]["path"])
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle(
                (160, 160, 351, 351),
                fill=(30, 80, 160, 254),
            )
            image.save(source)
            self.write_json(intent_path, intent)

            result = self.run_cli(
                "advance",
                "--job",
                str(job),
                "--intent",
                str(intent_path),
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["error"]["code"], "CANONICAL_ALPHA_GATE_FAILED")
            self.assertFalse(job.exists())

    def test_checkpoint_response_schema_is_closed_and_phase_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            result = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            state = json.loads(result.stdout)["result"]["state"]
            schema = state["checkpoint"]["response_schema"]
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["checkpoint_id"]["const"], state["checkpoint_id"])
            self.assertEqual(schema["properties"]["job_revision"]["const"], state["revision"])
            self.assertEqual(schema["properties"]["context_sha256"]["const"], state["context_sha256"])
            branches = schema["properties"]["payload"]["oneOf"]
            self.assertTrue(all(branch["properties"]["gate"]["const"] == "canonical" for branch in branches))
            self.assertEqual({branch["properties"]["decision"]["const"] for branch in branches}, {"approved", "changes-requested"})
            self.assertEqual(set(schema["required"]), {"schema_version", "checkpoint_id", "job_revision", "context_sha256", "kind", "payload"})

    def test_pixel_art_is_a_typed_unsupported_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root, "pixel-art/v1"))
            result = self.run_cli("advance", "--job", str(root / "job"), "--intent", str(intent_path), "--json")
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(payload["error"]["code"], "UNSUPPORTED_CAPABILITY")
            self.assertFalse((root / "job").exists())

    def test_replay_is_idempotent_and_stale_response_preserves_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "intent.json"
            job = root / "job"
            self.write_json(intent_path, self.intent(root))
            first = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            state_bytes = (job / "state.json").read_bytes()
            replay = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
            self.assertEqual((job / "state.json").read_bytes(), state_bytes)
            state = json.loads(state_bytes)
            response_path = root / "response.json"
            self.write_json(response_path, {
                "schema_version": "spritesheet-production-response/v1",
                "checkpoint_id": state["checkpoint_id"], "job_revision": state["revision"] + 1,
                "context_sha256": state["context_sha256"], "kind": "review",
                "payload": {"gate": "motion-blueprint", "decision": "approved", "authority": "user", "evidence": "reviewed together"},
            })
            stale = self.run_cli("advance", "--job", str(job), "--response", str(response_path), "--json")
            self.assertEqual(json.loads(stale.stdout)["error"]["code"], "STALE_CHECKPOINT")
            self.assertEqual((job / "state.json").read_bytes(), state_bytes)

    def test_legacy_job_protocol_rejects_response_and_intent_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for label, schema_version in (
                ("schema-v1", "spritesheet-production-job/v1"),
                ("v2-missing-pixel-protocol", "spritesheet-production-job/v2"),
            ):
                with self.subTest(protocol=label):
                    case_root = root / label
                    case_root.mkdir()
                    job = case_root / "job"
                    intent_path = case_root / "intent.json"
                    intent = self.intent(case_root)
                    self.write_json(intent_path, intent)
                    created = self.run_cli(
                        "advance",
                        "--job",
                        str(job),
                        "--intent",
                        str(intent_path),
                        "--json",
                    )
                    self.assertEqual(
                        created.returncode, 0, created.stdout + created.stderr
                    )

                    state_path = job / "state.json"
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    response_path = case_root / "response.json"
                    self.write_json(response_path, {
                        "schema_version": "spritesheet-production-response/v1",
                        "checkpoint_id": state["checkpoint_id"],
                        "job_revision": state["revision"],
                        "context_sha256": state["context_sha256"],
                        "kind": "review",
                        "payload": {
                            "gate": "canonical",
                            "decision": "approved",
                            "authority": "user",
                            "evidence": "approved the persisted checkpoint",
                        },
                    })
                    state["schema_version"] = schema_version
                    state.pop("pixel_protocol_id")
                    self.write_json(state_path, state)
                    stale_tree = self.tree_bytes(job)

                    resumed = self.run_cli(
                        "advance",
                        "--job",
                        str(job),
                        "--response",
                        str(response_path),
                        "--json",
                    )
                    self.assertEqual(resumed.returncode, 1)
                    self.assertEqual(
                        json.loads(resumed.stdout)["error"]["code"],
                        "JOB_PROTOCOL_STALE",
                    )
                    self.assertEqual(self.tree_bytes(job), stale_tree)

                    intent["base_revision"] = state["revision"]
                    intent["output_scope"] = {
                        "delivery_dir": str(case_root / "revised-delivery")
                    }
                    revised_intent_path = case_root / "revised-intent.json"
                    self.write_json(revised_intent_path, intent)
                    updated = self.run_cli(
                        "advance",
                        "--job",
                        str(job),
                        "--intent",
                        str(revised_intent_path),
                        "--json",
                    )
                    self.assertEqual(updated.returncode, 1)
                    self.assertEqual(
                        json.loads(updated.stdout)["error"]["code"],
                        "JOB_PROTOCOL_STALE",
                    )
                    self.assertEqual(self.tree_bytes(job), stale_tree)

    def test_public_verify_rejects_legacy_rendering_protocols_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = pipeline_tests.SpritesheetPipelineTests(methodName="runTest")
            request_path, request = helper.make_production_request(root)
            outline = {
                "enabled": True,
                "target_width": 2,
                "color": [7, 8, 9, 255],
            }
            helper.enable_outline_for_production_request(root, request, outline)
            helper.write_json(request_path, request)
            current_package = root / "current-package"
            built = helper.run_cli(
                "build-package",
                "--request",
                str(request_path),
                "--output-dir",
                str(current_package),
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)

            mutations = {
                "receipt-v1": lambda rendering: rendering.update(
                    schema_version="spritesheet-rendering-receipt/v1"
                ),
                "outline-v2": lambda rendering: rendering.update(
                    outline_algorithm="outward-silhouette-maxfilter-opaque-alpha/v2"
                ),
            }
            for label, mutate in mutations.items():
                with self.subTest(protocol=label):
                    package = root / label
                    shutil.copytree(current_package, package)
                    manifest_path = package / "manifest.json"
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    mutate(manifest["rendering"])
                    self.write_json(manifest_path, manifest)
                    stale_tree = self.tree_bytes(package)

                    verified = self.run_cli(
                        "verify", "--subject", str(manifest_path), "--json"
                    )

                    self.assertEqual(verified.returncode, 1)
                    self.assertEqual(
                        json.loads(verified.stdout)["error"]["code"],
                        "LEGACY_ADAPTER_FAILED",
                    )
                    self.assertEqual(self.tree_bytes(package), stale_tree)

    def test_read_only_intent_accepts_subject_without_production_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intent_path = root / "review.json"
            self.write_json(intent_path, {
                "schema_version": "spritesheet-production-intent/v1", "mode": "review",
                "output_scope": {"subject": str(root / "missing")}, "runtime_scope": None,
            })
            result = self.run_cli("advance", "--job", str(root / "job"), "--intent", str(intent_path), "--json")
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "UNSUPPORTED_SUBJECT")
            self.assertFalse((root / "missing").exists())

    def test_identity_source_byte_change_creates_a_material_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            intent = self.intent(root)
            self.write_json(intent_path, intent)
            first = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            source = Path(intent["identity"]["sources"][0]["path"])
            self.write_rgba(source, 91)
            intent["base_revision"] = json.loads((job / "state.json").read_text(encoding="utf-8"))["revision"]
            self.write_json(intent_path, intent)
            revised = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            self.assertEqual(json.loads(revised.stdout)["result"]["state"]["revision"], 2)
            self.assertTrue((job / "artifacts-r1").is_dir())
            self.assertTrue((job / "artifacts-r2").is_dir())

    def test_source_bytes_and_output_scope_change_reopens_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            intent = self.intent(root)
            self.write_json(intent_path, intent)
            created = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            created_state = json.loads(created.stdout)["result"]["state"]
            self.write_rgba(Path(intent["identity"]["sources"][0]["path"]), 119)
            intent["base_revision"] = created_state["revision"]
            intent["output_scope"] = {"delivery_dir": str(root / "changed-delivery")}
            self.write_json(intent_path, intent)
            revised = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            state = json.loads(revised.stdout)["result"]["state"]
            self.assertEqual(state["material_revision"], 2)
            self.assertEqual(state["phase"], "awaiting-canonical-review")
            self.assertTrue((job / "artifacts-r2").is_dir())

    def test_intent_invalidation_preserves_only_authoritative_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            intent = self.intent(root)
            self.write_json(intent_path, intent)
            created = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            state = json.loads(created.stdout)["result"]["state"]
            intent["base_revision"] = state["revision"]
            intent["output_scope"] = {"delivery_dir": str(root / "delivery")}
            self.write_json(intent_path, intent)
            output_update = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            output_state = json.loads(output_update.stdout)["result"]["state"]
            self.assertEqual(output_state["material_revision"], 1)
            self.assertEqual(output_state["outputs"]["canonical_references"], state["outputs"]["canonical_references"])

            response = root / "response.json"
            self.write_json(response, {"schema_version": "spritesheet-production-response/v1", "checkpoint_id": output_state["checkpoint_id"], "job_revision": output_state["revision"], "context_sha256": output_state["context_sha256"], "kind": "review", "payload": {"gate": "canonical", "decision": "approved", "authority": "user", "evidence": "approved"}})
            approved = self.run_cli("advance", "--job", str(job), "--response", str(response), "--json")
            approved_state = json.loads(approved.stdout)["result"]["state"]
            identity_path = approved_state["outputs"]["identity_bible"]
            intent["base_revision"] = approved_state["revision"]
            intent["clips"][0]["transition"] = "revised-ready"
            self.write_json(intent_path, intent)
            clip_update = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            clip_state = json.loads(clip_update.stdout)["result"]["state"]
            self.assertEqual(clip_state["material_revision"], 2)
            self.assertEqual(clip_state["phase"], "awaiting-production-blueprint-review")
            self.assertEqual(clip_state["outputs"]["identity_bible"], identity_path)
            self.assertIn("canonical", clip_state["approvals"])

            intent["base_revision"] = clip_state["revision"]
            intent["clips"][0]["direction"] = "west"
            self.write_json(intent_path, intent)
            binding_update = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(binding_update.returncode, 0, binding_update.stdout + binding_update.stderr)
            binding_state = json.loads(binding_update.stdout)["result"]["state"]
            self.assertEqual(binding_state["material_revision"], 3)
            self.assertEqual(binding_state["phase"], "awaiting-canonical-review")
            self.assertNotIn("identity_bible", binding_state["outputs"])
            self.assertNotIn("canonical", binding_state["approvals"])

    def test_checkpoint_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            self.assertEqual(self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json").returncode, 0)
            state = json.loads((job / "state.json").read_text(encoding="utf-8"))
            state["checkpoint"]["question"] = "tampered"
            self.write_json(job / "state.json", state)
            result = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "JOB_STATE_CORRUPT")

    def test_failed_state_commit_preserves_previous_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            self.assertEqual(self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json").returncode, 0)
            previous = (job / "state.json").read_bytes()
            state = json.loads(previous)
            response = root / "response.json"
            self.write_json(response, {"schema_version": "spritesheet-production-response/v1", "checkpoint_id": state["checkpoint_id"], "job_revision": state["revision"], "context_sha256": state["context_sha256"], "kind": "review", "payload": {"gate": "canonical", "decision": "approved", "authority": "user", "evidence": "approved"}})
            failed = self.run_cli("advance", "--job", str(job), "--response", str(response), "--json", extra_env={"SPRITESHEET_PRODUCTION_FAIL_AT": "state-commit"})
            self.assertEqual(json.loads(failed.stdout)["error"]["code"], "INJECTED_FAILURE")
            self.assertEqual((job / "state.json").read_bytes(), previous)

    def test_initial_state_commit_failure_cleans_artifacts_and_retries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            failed = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json", extra_env={"SPRITESHEET_PRODUCTION_FAIL_AT": "state-commit"})
            self.assertEqual(json.loads(failed.stdout)["error"]["code"], "INJECTED_FAILURE")
            self.assertFalse((job / "state.json").exists())
            self.assertFalse((job / "artifacts-r1").exists())
            retried = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(retried.returncode, 0, retried.stdout + retried.stderr)

    def test_new_job_never_reuses_uncommitted_artifact_residue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            residue = job / "artifacts-r1" / "canonical-hero"
            residue.mkdir(parents=True)
            sentinel = residue / "canonical-reference-candidate.png"
            sentinel.write_bytes(b"untrusted residue")
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            result = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(json.loads(result.stdout)["error"]["code"], "UNCOMMITTED_JOB_RESIDUE")
            self.assertEqual(sentinel.read_bytes(), b"untrusted residue")
            self.assertFalse((job / "state.json").exists())

    def test_concurrent_duplicate_response_commits_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            self.assertEqual(self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json").returncode, 0)
            state = json.loads((job / "state.json").read_text(encoding="utf-8"))
            response = root / "response.json"
            self.write_json(response, {"schema_version": "spritesheet-production-response/v1", "checkpoint_id": state["checkpoint_id"], "job_revision": state["revision"], "context_sha256": state["context_sha256"], "kind": "review", "payload": {"gate": "canonical", "decision": "approved", "authority": "user", "evidence": "approved"}})
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.run_cli("advance", "--job", str(job), "--response", str(response), "--json"), range(2)))
            codes = sorted(json.loads(result.stdout).get("error", {}).get("code", "OK") for result in results)
            self.assertEqual(codes, ["OK", "STALE_CHECKPOINT"])
            committed = json.loads((job / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(committed["revision"], 2)
            self.assertEqual(committed["material_revision"], 1)

    def test_rejects_symlink_oversize_and_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real.png"
            self.write_rgba(real, 8)
            linked = root / "linked.png"
            linked.symlink_to(real)
            intent = self.intent(root)
            intent["identity"]["sources"][0]["path"] = str(linked)
            intent_path = root / "intent.json"
            self.write_json(intent_path, intent)
            linked_result = self.run_cli("advance", "--job", str(root / "job-a"), "--intent", str(intent_path), "--json")
            self.assertNotEqual(linked_result.returncode, 0)
            oversized = root / "oversized.json"
            oversized.write_bytes(b"{" + b" " * (4 * 1024 * 1024 + 1) + b"}")
            oversized_result = self.run_cli("advance", "--job", str(root / "job-b"), "--intent", str(oversized), "--json")
            self.assertNotEqual(oversized_result.returncode, 0)
            overlap = self.intent(root)
            overlap["output_scope"] = {"delivery_dir": str(root / "job-c" / "delivery")}
            self.write_json(intent_path, overlap)
            overlap_result = self.run_cli("advance", "--job", str(root / "job-c"), "--intent", str(intent_path), "--json")
            self.assertEqual(json.loads(overlap_result.stdout)["error"]["code"], "PATH_OVERLAP")

    def test_complete_gate_sequence_builds_reviews_seals_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = root / "job"
            intent_path = root / "intent.json"
            self.write_json(intent_path, self.intent(root))
            result = self.run_cli("advance", "--job", str(job), "--intent", str(intent_path), "--json")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            def respond(
                kind: str,
                payload: dict[str, object],
                *,
                fail_at: str | None = None,
            ) -> dict[str, object]:
                state = json.loads((job / "state.json").read_text(encoding="utf-8"))
                response = root / "response.json"
                self.write_json(response, {
                    "schema_version": "spritesheet-production-response/v1",
                    "checkpoint_id": state["checkpoint_id"], "job_revision": state["revision"],
                    "context_sha256": state["context_sha256"], "kind": kind, "payload": payload,
                })
                completed = self.run_cli(
                    "advance", "--job", str(job), "--response", str(response), "--json",
                    extra_env={"SPRITESHEET_PRODUCTION_FAIL_AT": fail_at} if fail_at else None,
                )
                if fail_at:
                    self.assertTrue(completed.stdout, completed.stderr)
                    self.assertEqual(json.loads(completed.stdout)["error"]["code"], "INJECTED_FAILURE", f"{fail_at}: {completed.stdout}")
                    return state
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                return json.loads(completed.stdout)["result"]["state"]

            respond("review", {"gate": "canonical", "decision": "approved", "authority": "user", "evidence": "approved prepared canonicals"})
            blueprint_state = respond("review", {"gate": "motion-blueprint", "decision": "approved", "authority": "user", "evidence": "approved current blueprint"})
            asset_schema = blueprint_state["checkpoint"]["response_schema"]["properties"]["payload"]["properties"]["assets"]
            self.assertEqual(asset_schema["minItems"], 2)
            self.assertEqual(asset_schema["maxItems"], 2)
            self.assertEqual(asset_schema["items"]["properties"]["id"]["enum"], ["k0", "k3"])
            self.assertEqual(asset_schema["items"]["properties"]["path"]["pattern"], "^/")
            blueprint_bytes = (job / "state.json").read_bytes()
            invalid_asset_response = root / "invalid-asset-response.json"
            self.write_json(invalid_asset_response, {
                "schema_version": "spritesheet-production-response/v1",
                "checkpoint_id": blueprint_state["checkpoint_id"], "job_revision": blueprint_state["revision"],
                "context_sha256": blueprint_state["context_sha256"], "kind": "input",
                "payload": {"assets": [{"id": "k0", "path": 7}, {"id": "k3", "path": "/tmp/missing.png"}]},
            })
            invalid_asset = self.run_cli("advance", "--job", str(job), "--response", str(invalid_asset_response), "--json")
            self.assertEqual(json.loads(invalid_asset.stdout)["error"]["code"], "INVALID_CONTRACT")
            self.assertEqual((job / "state.json").read_bytes(), blueprint_bytes)
            identity = json.loads(Path(blueprint_state["outputs"]["identity_bible"]).read_text(encoding="utf-8"))
            self.assertEqual(identity["approval"]["evidence"], "approved prepared canonicals")
            frame_paths: dict[str, str] = {}
            for index, frame_id in enumerate(("k0", "i1", "i2", "k3"), start=1):
                frame = root / f"{frame_id}.png"
                self.write_rgba(frame, 30 + index, (512, 512))
                frame_paths[frame_id] = str(frame)
            respond("input", {"assets": [{"id": frame_id, "path": frame_paths[frame_id]} for frame_id in ("k0", "k3")]})
            self.write_rgba(Path(frame_paths["k0"]), 201, (512, 512))
            keyframe_state = respond("review", {"gate": "keyframe-set", "decision": "approved", "authority": "user", "evidence": "approved keyframes"})
            self.assertEqual(keyframe_state["phase"], "awaiting-spacing-plan-input")
            spacing_input_state = respond("input", {
                "spacing_plan": {"clips": [{
                    "id": "walk-east", "durations_ms": [100, 100, 100, 100], "events": [],
                    "positions": [
                        {"id": "k0", "role": "keyframe", "phase": "contact", "events": [], "spacing": "start", "arc": "level", "contacts": ["front foot"], "transition_from_previous": "entry", "transition_to_next": "ease-out"},
                        {"id": "i1", "role": "in-between", "phase": "down", "events": [], "spacing": "ease-out", "arc": "down", "contacts": [], "transition_from_previous": "accelerate", "transition_to_next": "continue"},
                        {"id": "i2", "role": "in-between", "phase": "passing", "events": [], "spacing": "ease-in", "arc": "up", "contacts": [], "transition_from_previous": "continue", "transition_to_next": "decelerate"},
                        {"id": "k3", "role": "keyframe", "phase": "contact-opposite", "events": [], "spacing": "end", "arc": "level", "contacts": ["rear foot"], "transition_from_previous": "ease-in", "transition_to_next": "exit"},
                    ],
                }]},
            })
            self.assertEqual(spacing_input_state["phase"], "awaiting-spacing-plan-review")
            self.assertIn("spacing_plan", spacing_input_state["checkpoint"]["presentation"])
            approved_spacing = respond("review", {"gate": "spacing-plan", "decision": "approved", "authority": "user", "evidence": "approved spacing"})
            serialized_spacing = json.loads(Path(approved_spacing["outputs"]["spacing_plans"][0]).read_text(encoding="utf-8"))["content"]
            self.assertEqual(serialized_spacing, spacing_input_state["checkpoint"]["presentation"]["evidence_contents"][0])
            respond("input", {"assets": [{"id": frame_id, "path": frame_paths[frame_id]} for frame_id in ("i1", "i2")]})
            sequence_payload = {"gate": "sequence", "decision": "approved", "authority": "user", "evidence": "approved sequence"}
            sequence_state_bytes = (job / "state.json").read_bytes()
            for failure in ("build", "diagnostics", "state-commit"):
                respond("review", sequence_payload, fail_at=failure)
                self.assertEqual((job / "state.json").read_bytes(), sequence_state_bytes)
                self.assertFalse((job / "artifacts-r1" / "package").exists())
                self.assertFalse((job / "artifacts-r1" / "diagnostics").exists())
            staged_state = respond("review", sequence_payload)
            self.assertEqual(staged_state["phase"], "awaiting-package-review")
            rework_subject = staged_state["outputs"]["package_review_subject_ids"][0]
            rework_state = respond("review", {
                "gate": "package", "decision": "changes-requested", "authority": "user", "evidence": "sequence needs revision",
                "observations": [{"subject_id": rework_subject, "classification": "reviewed", "disposition": "rework-required", "statement": "Revise the in-between spacing"}],
                "return_to": "sequence",
            })
            self.assertEqual(rework_state["phase"], "awaiting-sequence-input")
            self.assertEqual(rework_state["material_revision"], 2)
            for invalidated in ("production_request", "package_manifest", "diagnostics", "review_presentation", "package_review_subject_ids"):
                self.assertNotIn(invalidated, rework_state["outputs"])
            respond("input", {"assets": [{"id": frame_id, "path": frame_paths[frame_id]} for frame_id in ("i1", "i2")]})
            staged_state = respond("review", sequence_payload)
            self.assertEqual(staged_state["phase"], "awaiting-package-review")
            package_payload = {
                "gate": "package", "decision": "approved", "authority": "user", "evidence": "approved diagnostic presentation",
                "observations": [{"subject_id": subject_id, "classification": "reviewed", "disposition": "acceptable", "statement": "Complete bound presentation reviewed"} for subject_id in staged_state["outputs"]["package_review_subject_ids"]],
            }
            package_state_bytes = (job / "state.json").read_bytes()
            for failure in ("seal", "state-commit"):
                respond("review", package_payload, fail_at=failure)
                self.assertEqual((job / "state.json").read_bytes(), package_state_bytes)
                current_artifacts = job / f"artifacts-r{staged_state['material_revision']}"
                self.assertFalse((current_artifacts / "sealed-delivery").exists())
                self.assertFalse((current_artifacts / "review-packet.json").exists())
                self.assertFalse((current_artifacts / "delivery-request.json").exists())
            final_state = respond("review", package_payload)
            self.assertEqual(final_state["phase"], "package-ready")
            manifest = Path(final_state["outputs"]["package_manifest"])
            verified = self.run_cli("verify", "--subject", str(manifest), "--json")
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertEqual(json.loads(verified.stdout)["result"]["subject_status"], "pixel-package-verified")
            delivery = Path(final_state["outputs"]["sealed_delivery"]).parent
            delivery_verified = self.run_cli("verify", "--subject", str(delivery), "--json")
            self.assertEqual(delivery_verified.returncode, 0, delivery_verified.stdout + delivery_verified.stderr)


if __name__ == "__main__":
    unittest.main()
