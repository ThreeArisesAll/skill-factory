from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPT = Path(__file__).parents[1] / "scripts" / "spritesheet_pipeline.py"


class SpritesheetPipelineTests(unittest.TestCase):
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

    @staticmethod
    def write_rgba(path: Path, size: tuple[int, int], seed: int) -> None:
        width, height = size
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            (8, 8, width - 9, height - 9),
            fill=(
                (seed * 31) % 256,
                (seed * 67) % 256,
                (seed * 101) % 256,
                255,
            ),
        )
        draw.rectangle((18, seed % 7 + 10, 29, seed % 7 + 21), fill=(255, seed, 100, 192))
        image.save(path)

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def prepare_fixture(
        self,
        root: Path,
        name: str,
        seed: int,
        outline: dict[str, object] | None = None,
        output_name: str | None = None,
    ) -> tuple[Path, Path, Path]:
        source = root / f"{name}-source.png"
        self.write_rgba(source, (400, 400), seed)
        request = root / f"{name}-authoring.json"
        self.write_json(
            request,
            {
                "schema_version": "canonical-authoring-request/v3",
                "canonical_id": name,
                "source": str(source),
                "target": {"frame_width": 32, "frame_height": 32},
                "outline": outline or {"enabled": False, "target_width": "none"},
            },
        )
        output = root / (output_name or f"{name}-prepared")
        prepared = self.run_cli(
            "prepare-canonical",
            "--request",
            str(request),
            "--output-dir",
            str(output),
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        return (
            output / "canonical-reference-candidate.png",
            output / "canonical-reference-evidence.json",
            output / "canonical-admission-proof.json",
        )

    def make_production_request(
        self,
        root: Path,
        *,
        repeat_opening_cell: bool = False,
        columns: int = 2,
        canonical_output_name: str | None = None,
    ) -> tuple[Path, dict[str, object]]:
        canonical, canonical_evidence, canonical_proof = self.prepare_fixture(
            root,
            "canonical",
            20,
            output_name=canonical_output_name,
        )
        frame_paths: dict[str, Path] = {}
        for index, frame_id in enumerate(("k0", "i1", "i2", "k3"), start=1):
            path = root / f"{frame_id}.png"
            self.write_rgba(path, (512, 512), index)
            frame_paths[frame_id] = path
        hashes = {artifact_id: hashlib.sha256(path.read_bytes()).hexdigest() for artifact_id, path in frame_paths.items()}
        canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
        admission_hash = hashlib.sha256(canonical_proof.read_bytes()).hexdigest()
        frames: list[dict[str, object]] = [
            {"id": "k0", "role": "keyframe", "path": str(frame_paths["k0"])},
            {
                "id": "i1",
                "role": "in-between",
                "path": str(frame_paths["i1"]),
                "previous_keyframe": "k0",
                "next_keyframe": "k3",
            },
            {
                "id": "i2",
                "role": "in-between",
                "path": str(frame_paths["i2"]),
                "previous_keyframe": "k0",
                "next_keyframe": "k3",
            },
            {"id": "k3", "role": "keyframe", "path": str(frame_paths["k3"])},
        ]
        request_data: dict[str, object] = {
            "schema_version": "spritesheet-production-request/v3",
            "contract": {
                "frame_width": 32,
                "frame_height": 32,
                "frame_count": 5 if repeat_opening_cell else 4,
                "high_resolution_short_side": 512,
                "sampler": "lanczos-premultiplied-v1",
                "outline": {"enabled": False, "target_width": "none"},
                "animation_origin": [0, 0],
                "anchor": [16, 31],
                "safe_bounds": [2, 2, 30, 30],
            },
            "canonical_references": [
                {
                    "id": "canonical",
                    "path": str(canonical),
                    "evidence_path": str(canonical_evidence),
                    "proof_path": str(canonical_proof),
                },
            ],
            "clips": [
                {
                    "id": "action-east",
                    "canonical_reference": "canonical",
                    "loop": repeat_opening_cell,
                    "repeat_opening_cell": repeat_opening_cell,
                    "direction": "east",
                    "camera": "orthographic-side",
                    "root_motion": "in-place",
                    "transition": "ready",
                    "terminal_hold": not repeat_opening_cell,
                    "durations_ms": [100] * (5 if repeat_opening_cell else 4),
                    "events": [{"name": "impact", "position": 2}],
                    "frames": frames,
                },
            ],
            "reviews": [
                {
                    "id": "canonical-review",
                    "gate": "canonical-approval",
                    "subject_ids": ["canonical"],
                    "subject_sha256": {"canonical": canonical_hash},
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved canonical reference",
                    "declared_order": 1,
                    "admission_sha256": {
                        "canonical": admission_hash,
                    },
                },
                {
                    "id": "keyframe-review",
                    "gate": "keyframe-set-approval",
                    "subject_ids": ["canonical", "k0", "k3"],
                    "subject_sha256": {
                        "canonical": canonical_hash,
                        "k0": hashes["k0"],
                        "k3": hashes["k3"],
                    },
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved keyframe set",
                    "declared_order": 2,
                    "admission_sha256": {
                        "canonical": admission_hash,
                    },
                },
                {
                    "id": "sequence-review",
                    "gate": "sequence-approval",
                    "subject_ids": ["canonical", "k0", "i1", "i2", "k3"],
                    "subject_sha256": {"canonical": canonical_hash, **hashes},
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved sequence",
                    "declared_order": 3,
                    "admission_sha256": {
                        "canonical": admission_hash,
                    },
                },
            ],
            "grid": {"columns": columns, "order": "row-major"},
        }
        request = root / "production.json"
        self.write_json(request, request_data)
        return request, request_data

    def test_public_flow_accepts_prepare_bundle_named_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, request_data = self.make_production_request(root, canonical_output_name="evidence")
            proof_path = Path(request_data["canonical_references"][0]["proof_path"])
            proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            self.assertEqual(
                {review["admission_sha256"]["canonical"] for review in request_data["reviews"]},
                {proof_hash},
            )
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            verified = self.run_cli("verify-package", "--manifest", str(output / "manifest.json"))

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_prepare_canonical_without_outline_is_atomic_and_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            self.write_rgba(source, (80, 40), 1)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 16},
                    "outline": {"enabled": False, "target_width": "none"},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            candidate = output / "canonical-reference-candidate.png"
            evidence = output / "canonical-reference-evidence.json"
            self.assertTrue(candidate.is_file())
            self.assertTrue(evidence.is_file())
            with Image.open(candidate) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.size, (1024, 512))
            record = json.loads(evidence.read_text(encoding="utf-8"))
            self.assertEqual(record["schema_version"], "canonical-reference-evidence/v3")
            self.assertEqual(record["candidate"]["sha256"], hashlib.sha256(candidate.read_bytes()).hexdigest())
            self.assertEqual(record["derivation"]["normalization"], "normalize-to-canvas/lanczos-premultiplied-v1")
            self.assertEqual(record["derivation"]["outline"], "identity/v1")
            self.assertNotIn("witness", record)
            source_evidence = output / record["source"]["path"]
            self.assertEqual(source_evidence.read_bytes(), source.read_bytes())
            self.assertEqual(
                {path.relative_to(output).as_posix() for path in output.rglob("*.png")},
                {"canonical-reference-candidate.png", record["source"]["path"]},
            )
            proof = output / "canonical-admission-proof.json"
            self.assertTrue(proof.is_file())
            proof_record = json.loads(proof.read_text())
            self.assertEqual(proof_record["canonical_reference"]["id"], "canonical")
            self.assertEqual(
                proof_record["authoring_evidence_sha256"],
                hashlib.sha256(evidence.read_bytes()).hexdigest(),
            )
            self.assertNotIn("type", record["candidate"])
            self.assertEqual(record["metrics"]["short_side"], 512)
            names = " ".join(path.name.lower() for path in output.rglob("*"))
            self.assertNotIn("pre-master", names)
            self.assertNotIn("master", names)
            self.assertNotIn("target", names)

    def test_prepare_canonical_adds_resolved_outward_outline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            self.write_rgba(source, (64, 64), 2)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads((output / "canonical-reference-evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["outline"]["resolved_high_resolution_width"], 32)
            with Image.open(output / "canonical-reference-candidate.png") as image:
                self.assertIn((7, 8, 9, 255), image.get_flattened_data())

    def test_prepare_rejects_invisible_outline_color(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            self.write_rgba(source, (64, 64), 2)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {"enabled": True, "target_width": 2, "color": [7, 8, 9, 0]},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 1)
            self.assertIn("alpha must be greater than zero", result.stdout)
            self.assertFalse(output.exists())

    def test_prepare_rejects_symlinked_source_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_source = root / "real-source.png"
            self.write_rgba(real_source, (64, 64), 2)
            source = root / "source.png"
            source.symlink_to(real_source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {"enabled": False, "target_width": "none"},
                },
            )
            output = root / "canonical"

            rejected = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertFalse(output.exists())

    def test_outline_preserves_every_existing_nontransparent_pixel(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            image.putpixel((30, 30), (200, 100, 50, 255))
            image.putpixel((31, 30), (100, 50, 25, 128))
            image.save(source)
            outputs = []
            for enabled in (False, True):
                request = root / f"request-{enabled}.json"
                self.write_json(
                    request,
                    {
                        "schema_version": "canonical-authoring-request/v3",
                        "canonical_id": f"canonical-{enabled}",
                        "source": str(source),
                        "target": {"frame_width": 32, "frame_height": 32},
                        "outline": {
                            "enabled": enabled,
                            "target_width": 2 if enabled else "none",
                            **({"color": [7, 8, 9, 255]} if enabled else {}),
                        },
                    },
                )
                output = root / f"canonical-{enabled}"
                result = self.run_cli(
                    "prepare-canonical",
                    "--request",
                    str(request),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                with Image.open(output / "canonical-reference-candidate.png") as candidate:
                    outputs.append(candidate.copy())
            plain, outlined = outputs
            plain_pixels = list(plain.get_flattened_data())
            outlined_pixels = list(outlined.get_flattened_data())
            for plain_pixel, outlined_pixel in zip(plain_pixels, outlined_pixels, strict=True):
                if plain_pixel[3] > 0:
                    self.assertEqual(plain_pixel, outlined_pixel)

    def test_enabled_outline_expands_even_when_source_already_has_black_edge_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "black-edged-source.png"
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((12, 12, 51, 51), fill=(0, 0, 0, 255))
            draw.rectangle((14, 14, 49, 49), fill=(190, 80, 40, 255))
            image.save(source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {"enabled": True, "target_width": 1, "color": [0, 0, 0, 255]},
                },
            )
            output = root / "prepared"

            prepared = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            evidence = json.loads((output / "canonical-reference-evidence.json").read_text())
            plain_request = root / "plain-request.json"
            self.write_json(
                plain_request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "plain-canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {"enabled": False, "target_width": "none"},
                },
            )
            plain_output = root / "plain"
            plain_result = self.run_cli(
                "prepare-canonical", "--request", str(plain_request), "--output-dir", str(plain_output),
            )
            self.assertEqual(plain_result.returncode, 0, plain_result.stdout + plain_result.stderr)
            with Image.open(plain_output / "canonical-reference-candidate.png") as plain_image, Image.open(
                output / "canonical-reference-candidate.png",
            ) as candidate:
                plain_bbox = plain_image.getchannel("A").getbbox()
                candidate_bbox = candidate.getchannel("A").getbbox()
            self.assertLess(candidate_bbox[0], plain_bbox[0])
            self.assertLess(candidate_bbox[1], plain_bbox[1])
            self.assertGreater(candidate_bbox[2], plain_bbox[2])
            self.assertGreater(candidate_bbox[3], plain_bbox[3])

    def test_prepare_failure_leaves_no_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            self.write_rgba(source, (32, 32), 3)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 512, "frame_height": 512},
                    "outline": {"enabled": False, "target_width": "none"},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 1)
            self.assertIn("smaller than 512", result.stdout)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".canonical-*")), [])

    def test_disabled_outline_requires_exact_none_width(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            self.write_rgba(source, (32, 32), 3)
            for target_width in (None, 0, "missing"):
                request = root / f"request-{target_width}.json"
                outline = {"enabled": False}
                if target_width != "missing":
                    outline["target_width"] = target_width
                self.write_json(
                    request,
                    {
                        "schema_version": "canonical-authoring-request/v3",
                        "canonical_id": f"canonical-{target_width}",
                        "source": str(source),
                        "target": {"frame_width": 32, "frame_height": 32},
                        "outline": outline,
                    },
                )
                output = root / f"canonical-{target_width}"

                result = self.run_cli(
                    "prepare-canonical",
                    "--request",
                    str(request),
                    "--output-dir",
                    str(output),
                )

                self.assertEqual(result.returncode, 1)
                self.assertFalse(output.exists())

    def test_prepare_rejects_empty_or_border_clipped_visible_content(self) -> None:
        for label, image in (
            ("empty", Image.new("RGBA", (32, 32), (0, 0, 0, 0))),
            ("border", Image.new("RGBA", (32, 32), (20, 30, 40, 255))),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.png"
                image.save(source)
                request = root / "request.json"
                self.write_json(
                    request,
                    {
                        "schema_version": "canonical-authoring-request/v3",
                        "canonical_id": f"canonical-{label}",
                        "source": str(source),
                        "target": {"frame_width": 32, "frame_height": 32},
                        "outline": {"enabled": False, "target_width": "none"},
                    },
                )
                output = root / "canonical"

                result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

                self.assertEqual(result.returncode, 1)
                self.assertFalse(output.exists())

    def test_builds_and_verifies_valid_four_frame_package_without_target_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"artifacts", "admission", "evidence", "manifest.json", "spritesheet.png"},
            )
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "spritesheet-package/v3")
            self.assertEqual(len(manifest["canonical_admissions"]), 1)
            admission = manifest["canonical_admissions"][0]
            self.assertTrue((output / admission["proof_path"]).is_file())
            self.assertNotIn("witness_path", admission)
            self.assertEqual(
                {artifact["type"] for artifact in manifest["artifacts"]},
                {"canonical-reference", "high-resolution-frame", "spritesheet"},
            )
            frame_artifacts = [
                artifact
                for artifact in manifest["artifacts"]
                if artifact["type"] == "high-resolution-frame"
            ]
            self.assertEqual([frame["role"] for frame in frame_artifacts], ["keyframe", "in-between", "in-between", "keyframe"])
            self.assertEqual(manifest["clips"][0]["frame_ids"], ["k0", "i1", "i2", "k3"])
            self.assertEqual(manifest["clips"][0]["durations_ms"], [100, 100, 100, 100])
            self.assertEqual(manifest["contract"]["anchor"], [16, 31])
            serialized = manifest_path.read_text(encoding="utf-8").lower()
            self.assertNotIn("target-frame", serialized)
            self.assertNotIn("target.png", serialized)
            self.assertEqual(list(output.rglob("*target*.png")), [])

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertIn("PASS MACHINE-VERIFIED cells", verified.stdout)
            self.assertIn("INFO DECLARED sampler", verified.stdout)
            self.assertIn("INFO REVIEWED canonical-approval", verified.stdout)

    def test_build_rejects_v1_and_invalid_graphs_without_partial_output(self) -> None:
        mutations = {
            "v1": lambda request: request.update(schema_version="spritesheet-production-request/v1"),
            "bracket": lambda request: request["clips"][0]["frames"][1].update(next_keyframe="i2"),
            "role": lambda request: request["clips"][0]["frames"][1].update(role="transition"),
            "review-coverage": lambda request: request["reviews"][2].update(subject_ids=["k0", "i1"]),
            "review-order": lambda request: request["reviews"][1].update(declared_order=3),
            "review-hash": lambda request: request["reviews"][0]["subject_sha256"].update(canonical="0" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                mutate(request)
                self.write_json(request_path, request)
                output = root / "package"

                result = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(output.exists())
                self.assertEqual(list(root.glob(".package-*")), [])

    def test_build_rejects_duplicate_high_resolution_pixels_and_changed_reviewed_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            first = Path(request["clips"][0]["frames"][0]["path"])
            second = Path(request["clips"][0]["frames"][1]["path"])
            second.write_bytes(first.read_bytes())
            output = root / "duplicate"

            duplicate = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(duplicate.returncode, 1)
            self.assertIn("distinct pixels", duplicate.stdout)
            self.assertFalse(output.exists())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            changed = Path(request["clips"][0]["frames"][2]["path"])
            self.write_rgba(changed, (512, 512), 99)
            output = root / "changed"

            stale_review = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(stale_review.returncode, 1)
            self.assertIn("subject_sha256", stale_review.stdout)
            self.assertFalse(output.exists())

    def test_repeat_opening_cell_reuses_first_pixels_without_a_second_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root, repeat_opening_cell=True)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["assembly"]["cells"]), 5)
            self.assertEqual(manifest["assembly"]["cells"][-1]["source"], "k0")
            self.assertTrue(manifest["assembly"]["cells"][-1]["repeated_opening"])
            self.assertEqual(set(manifest["sampling"]), {"algorithm", "proof"})
            with Image.open(output / "spritesheet.png") as sheet:
                first = sheet.crop((0, 0, 32, 32))
                closing = sheet.crop((0, 64, 32, 96))
                self.assertEqual(first.tobytes(), closing.tobytes())

    def test_verify_rejects_sheet_pixel_tampering_and_nonempty_unused_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root, columns=3)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            sheet_path = output / "spritesheet.png"
            with Image.open(sheet_path) as opened:
                sheet = opened.copy()
            sheet.putpixel((0, 0), (255, 0, 255, 255))
            sheet.putpixel((65, 33), (1, 2, 3, 255))
            sheet.save(sheet_path)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sheet_record = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "spritesheet")
            sheet_record["sha256"] = hashlib.sha256(sheet_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED cells", verified.stdout)
            self.assertIn("FAIL MACHINE-VERIFIED assembly.unused-cells", verified.stdout)

    def test_verify_rejects_orphan_artifact_and_review_binding_after_manifest_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            original = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "i1")
            orphan = dict(original, id="orphan")
            manifest["artifacts"].append(orphan)
            original["sha256"] = "f" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED artifacts.graph", verified.stdout)
            self.assertIn("FAIL MACHINE-VERIFIED reviews", verified.stdout)

    def test_verify_invalidates_downstream_reviews_when_canonical_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            canonical = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "canonical-reference")
            canonical_path = output / canonical["path"]
            self.write_rgba(canonical_path, (512, 512), 88)
            new_hash = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
            canonical["sha256"] = new_hash
            canonical_review = next(review for review in manifest["reviews"] if review["gate"] == "canonical-approval")
            canonical_review["subject_sha256"][canonical["id"]] = new_hash
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED reviews", verified.stdout)

    def test_build_requires_runtime_metadata_and_preserves_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            del request["clips"][0]["durations_ms"]
            self.write_json(request_path, request)
            output = root / "package"

            rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("durations_ms", rejected.stdout)
            self.assertFalse(output.exists())

    def test_build_rejects_relative_input_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            request["canonical_references"][0]["path"] = "canonical.png"
            self.write_json(request_path, request)
            output = root / "package"

            rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("absolute path", rejected.stdout)
            self.assertFalse(output.exists())

    def test_build_requires_admission_evidence_and_rejects_outline_skip_fields(self) -> None:
        mutations = {
            "missing-evidence": lambda request: request["canonical_references"][0].pop("evidence_path"),
            "already-outlined": lambda request: request["contract"]["outline"].update(already_outlined=True),
            "skip-outline": lambda request: request["contract"]["outline"].update(skip_outline=True),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                mutate(request)
                self.write_json(request_path, request)
                output = root / "package"

                rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

                self.assertEqual(rejected.returncode, 1)
                self.assertFalse(output.exists())

    def test_build_rejects_tampered_authoring_evidence_and_stale_proof(self) -> None:
        mutations = {
            "candidate-path": lambda evidence: evidence["candidate"].update(path="renamed.png"),
            "metrics": lambda evidence: evidence["metrics"].update(short_side=511),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                evidence_path = Path(request["canonical_references"][0]["evidence_path"])
                evidence = json.loads(evidence_path.read_text())
                mutate(evidence)
                evidence_path.write_text(json.dumps(evidence))
                output = root / "package"

                rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

                self.assertEqual(rejected.returncode, 1)
                self.assertFalse(output.exists())

    def test_build_rejects_symlinked_canonical_frame_source_evidence_and_proof_inputs(self) -> None:
        for input_kind in ("canonical", "frame", "source", "evidence", "proof"):
            with self.subTest(input_kind=input_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                canonical_entry = request["canonical_references"][0]
                if input_kind == "frame":
                    target = Path(request["clips"][0]["frames"][0]["path"])
                    field_owner = request["clips"][0]["frames"][0]
                    field = "path"
                elif input_kind == "canonical":
                    target = Path(canonical_entry["path"])
                    field_owner, field = canonical_entry, "path"
                elif input_kind in ("evidence", "proof"):
                    field = f"{input_kind}_path"
                    target = Path(canonical_entry[field])
                    field_owner = canonical_entry
                else:
                    evidence_path = Path(canonical_entry["evidence_path"])
                    evidence = json.loads(evidence_path.read_text())
                    target = evidence_path.parent / evidence["source"]["path"]
                    field_owner = None
                    field = ""
                if field_owner is not None:
                    link = root / f"{input_kind}-link{target.suffix}"
                    link.symlink_to(target)
                    field_owner[field] = str(link)
                    self.write_json(request_path, request)
                else:
                    real_source = root / "real-source.png"
                    target.rename(real_source)
                    target.symlink_to(real_source)
                output = root / "package"

                rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

                self.assertEqual(rejected.returncode, 1)
                self.assertFalse(output.exists())

    def test_build_reuses_approved_enabled_outline_canonical_bytes_without_reapplying_outline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 1, "color": [0, 0, 0, 255]}
            outlined_source = root / "outlined-source.png"
            outlined_image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            ImageDraw.Draw(outlined_image).rectangle((100, 100, 299, 299), fill=(120, 80, 40, 255))
            outlined_image.save(outlined_source)
            authoring_request = root / "outlined-authoring.json"
            self.write_json(
                authoring_request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(outlined_source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": outline,
                },
            )
            prepared_output = root / "outlined-prepared"
            prepared = self.run_cli(
                "prepare-canonical",
                "--request",
                str(authoring_request),
                "--output-dir",
                str(prepared_output),
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            canonical = prepared_output / "canonical-reference-candidate.png"
            evidence = prepared_output / "canonical-reference-evidence.json"
            proof_path = prepared_output / "canonical-admission-proof.json"
            request["contract"]["outline"] = outline
            request["canonical_references"][0] = {
                "id": "canonical",
                "path": str(canonical),
                "evidence_path": str(evidence),
                "proof_path": str(proof_path),
            }
            canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
            admission_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                review["subject_sha256"]["canonical"] = canonical_hash
                review["admission_sha256"]["canonical"] = admission_hash
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest = json.loads((output / "manifest.json").read_text())
            canonical_record = next(
                artifact for artifact in manifest["artifacts"] if artifact["type"] == "canonical-reference"
            )
            self.assertEqual((output / canonical_record["path"]).read_bytes(), canonical.read_bytes())

    def test_verify_replays_packaged_source_normalization_and_admission_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            admission = manifest["canonical_admissions"][0]
            source_path = output / admission["source_path"]
            self.write_rgba(source_path, (400, 400), 99)
            new_source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            new_source_path = output / "evidence" / f"{new_source_hash}.png"
            source_path.rename(new_source_path)
            proof_path = output / admission["proof_path"]
            proof = json.loads(proof_path.read_text())
            proof["source"]["sha256"] = new_source_hash
            proof_bytes = (json.dumps(proof, indent=2) + "\n").encode()
            new_proof_hash = hashlib.sha256(proof_bytes).hexdigest()
            new_proof_path = output / "admission" / f"{new_proof_hash}.json"
            new_proof_path.write_bytes(proof_bytes)
            proof_path.unlink()
            admission.update(
                source_path=f"evidence/{new_source_hash}.png",
                source_sha256=new_source_hash,
                proof_path=f"admission/{new_proof_hash}.json",
                proof_sha256=new_proof_hash,
            )
            for review in manifest["reviews"]:
                review["admission_sha256"]["canonical"] = new_proof_hash
            manifest_path.write_text(json.dumps(manifest))

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("does not pixel-match packaged admission evidence", verified.stdout)

    def test_verify_rejects_extra_files_absolute_paths_and_zero_columns_without_traceback(self) -> None:
        mutations = (
            "extra-file",
            "absolute-path",
            "zero-columns",
            "artifact-symlink",
            "huge-height",
            "huge-count",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request, _ = self.make_production_request(root)
                output = root / "package"
                built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                manifest_path = output / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if mutation == "extra-file":
                    (output / "undeclared.bin").write_bytes(b"undeclared")
                elif mutation == "absolute-path":
                    artifact = manifest["artifacts"][0]
                    artifact["path"] = str((output / artifact["path"]).resolve())
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                elif mutation == "zero-columns":
                    manifest["assembly"]["columns"] = 0
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                else:
                    if mutation == "artifact-symlink":
                        artifact = manifest["artifacts"][0]
                        artifact_path = output / artifact["path"]
                        hidden = output / "hidden.png"
                        artifact_path.rename(hidden)
                        artifact_path.symlink_to(hidden)
                    elif mutation == "huge-height":
                        manifest["contract"]["frame_height"] = 2**63
                        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    else:
                        manifest["contract"]["frame_count"] = 2**63
                        manifest["assembly"]["rows"] = 2**62
                        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

                self.assertEqual(verified.returncode, 1)
                self.assertNotIn("Traceback", verified.stderr)

    def test_build_rejects_non_png_container_with_png_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            canonical = Path(request["canonical_references"][0]["path"])
            with Image.open(canonical) as opened:
                opened.save(canonical, format="TIFF")
            self.write_json(request_path, request)
            output = root / "package"

            rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("PNG container", rejected.stdout)
            self.assertFalse(output.exists())

    def test_verify_hard_rejects_v1_and_canonical_as_a_frame_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["schema_version"] = "spritesheet-package/v1"
            manifest["clips"][0]["frame_ids"][1] = "canonical"
            manifest["assembly"]["cells"][1]["source"] = "canonical"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED schema_version", verified.stdout)
            self.assertIn("FAIL MACHINE-VERIFIED frame[canonical].artifact", verified.stdout)

    def test_verify_rejects_external_paths_and_malformed_unhashable_frame_ids_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"][0]["path"] = str(root / "canonical.png")
            manifest["clips"][0]["frame_ids"][1] = {}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertNotIn("Traceback", verified.stderr)
            self.assertIn("must be a normalized package-relative path", verified.stdout)

    def test_builds_two_canonical_references_and_verifier_requires_each_admission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            canonical_two, evidence_two, proof_two = self.prepare_fixture(root, "canonical-two", 40)
            request["canonical_references"].append(
                {
                    "id": "canonical-two",
                    "path": str(canonical_two),
                    "evidence_path": str(evidence_two),
                    "proof_path": str(proof_two),
                },
            )
            frames_two = []
            for index, (frame_id, role) in enumerate(
                (("k4", "keyframe"), ("i5", "in-between"), ("i6", "in-between"), ("k7", "keyframe")),
                start=10,
            ):
                path = root / f"{frame_id}.png"
                self.write_rgba(path, (512, 512), index)
                frame = {"id": frame_id, "role": role, "path": str(path)}
                if role == "in-between":
                    frame.update(previous_keyframe="k4", next_keyframe="k7")
                frames_two.append(frame)
            request["clips"].append(
                {
                    "id": "action-west",
                    "canonical_reference": "canonical-two",
                    "loop": False,
                    "repeat_opening_cell": False,
                    "direction": "west",
                    "camera": "orthographic-side",
                    "root_motion": "in-place",
                    "transition": "ready",
                    "terminal_hold": True,
                    "durations_ms": [90, 90, 90, 110],
                    "events": [{"name": "impact", "position": 1}],
                    "frames": frames_two,
                },
            )
            request["canonical_references"].reverse()
            request["contract"]["frame_count"] = 8
            canonical_two_hash = hashlib.sha256(canonical_two.read_bytes()).hexdigest()
            admission_two_hash = hashlib.sha256(proof_two.read_bytes()).hexdigest()
            second_hashes = {
                frame["id"]: hashlib.sha256(Path(frame["path"]).read_bytes()).hexdigest()
                for frame in frames_two
            }
            original_canonical, original_keyframes, original_sequence = request["reviews"]
            request["reviews"] = [
                {
                    "id": "canonical-review-two",
                    "gate": "canonical-approval",
                    "subject_ids": ["canonical-two"],
                    "subject_sha256": {"canonical-two": canonical_two_hash},
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved second canonical",
                    "declared_order": 1,
                    "admission_sha256": {"canonical-two": admission_two_hash},
                },
                dict(original_canonical, declared_order=2),
                dict(original_keyframes, declared_order=3),
                dict(original_sequence, declared_order=5),
                {
                    "id": "keyframe-review-two",
                    "gate": "keyframe-set-approval",
                    "subject_ids": ["canonical-two", "k4", "k7"],
                    "subject_sha256": {
                        "canonical-two": canonical_two_hash,
                        "k4": second_hashes["k4"],
                        "k7": second_hashes["k7"],
                    },
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved second keyframe set",
                    "declared_order": 4,
                    "admission_sha256": {"canonical-two": admission_two_hash},
                },
                {
                    "id": "sequence-review-two",
                    "gate": "sequence-approval",
                    "subject_ids": ["canonical-two", "k4", "i5", "i6", "k7"],
                    "subject_sha256": {"canonical-two": canonical_two_hash, **second_hashes},
                    "reviewer": "reviewer@example.com",
                    "evidence": "approved second sequence",
                    "declared_order": 6,
                    "admission_sha256": {"canonical-two": admission_two_hash},
                },
            ]
            request["reviews"].reverse()
            self.write_json(request_path, request)
            output = root / "package"

            result = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["clips"]), 2)
            self.assertEqual(len(manifest["reviews"]), 6)
            self.assertEqual(
                [review["gate"] for review in manifest["reviews"]],
                [
                    "canonical-approval",
                    "canonical-approval",
                    "keyframe-set-approval",
                    "keyframe-set-approval",
                    "sequence-approval",
                    "sequence-approval",
                ],
            )

            removed = next(
                admission
                for admission in manifest["canonical_admissions"]
                if admission["canonical_reference"] == "canonical-two"
            )
            manifest["canonical_admissions"].remove(removed)
            (output / removed["proof_path"]).unlink()
            (output / removed["source_path"]).unlink()
            for review in manifest["reviews"]:
                if "canonical-two" in review["subject_ids"]:
                    review["admission_sha256"] = {}
            manifest_path = output / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("canonical_admissions.graph", verified.stdout)

    def test_build_rejects_sequence_approval_before_all_canonical_gates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            duplicate_canonical, duplicate_evidence, duplicate_proof = self.prepare_fixture(
                root, "unused-canonical", 77,
            )
            request["canonical_references"].append(
                {
                    "id": "unused-canonical",
                    "path": str(duplicate_canonical),
                    "evidence_path": str(duplicate_evidence),
                    "proof_path": str(duplicate_proof),
                },
            )
            second_clip = json.loads(json.dumps(request["clips"][0]))
            second_clip.update(id="second", canonical_reference="unused-canonical")
            request["clips"].append(second_clip)
            for index, frame in enumerate(request["clips"][1]["frames"], start=10):
                new_id = f"second-{frame['id']}"
                new_path = root / f"{new_id}.png"
                self.write_rgba(new_path, (512, 512), index)
                frame["id"] = new_id
                frame["path"] = str(new_path)
            by_role = request["clips"][1]["frames"]
            for frame in by_role:
                if frame["role"] == "in-between":
                    frame["previous_keyframe"] = "second-k0"
                    frame["next_keyframe"] = "second-k3"
            request["contract"]["frame_count"] = 8
            hashes = {
                frame["id"]: hashlib.sha256(Path(frame["path"]).read_bytes()).hexdigest()
                for frame in by_role
            }
            canonical_hash = hashlib.sha256(duplicate_canonical.read_bytes()).hexdigest()
            admission_hash = hashlib.sha256(duplicate_proof.read_bytes()).hexdigest()
            request["reviews"].extend(
                [
                    {
                        "id": "second-canonical",
                        "gate": "canonical-approval",
                        "subject_ids": ["unused-canonical"],
                        "subject_sha256": {"unused-canonical": canonical_hash},
                        "reviewer": "reviewer@example.com",
                        "evidence": "second canonical",
                        "declared_order": 4,
                        "admission_sha256": {"unused-canonical": admission_hash},
                    },
                    {
                        "id": "second-keyframes",
                        "gate": "keyframe-set-approval",
                        "subject_ids": ["unused-canonical", "second-k0", "second-k3"],
                        "subject_sha256": {
                            "unused-canonical": canonical_hash,
                            "second-k0": hashes["second-k0"],
                            "second-k3": hashes["second-k3"],
                        },
                        "reviewer": "reviewer@example.com",
                        "evidence": "second keyframes",
                        "declared_order": 5,
                        "admission_sha256": {"unused-canonical": admission_hash},
                    },
                    {
                        "id": "second-sequence",
                        "gate": "sequence-approval",
                        "subject_ids": ["unused-canonical", *[frame["id"] for frame in by_role]],
                        "subject_sha256": {"unused-canonical": canonical_hash, **hashes},
                        "reviewer": "reviewer@example.com",
                        "evidence": "second sequence",
                        "declared_order": 6,
                        "admission_sha256": {"unused-canonical": admission_hash},
                    },
                ],
            )
            self.write_json(request_path, request)
            output = root / "package"

            rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("complete every canonical gate", rejected.stdout)
            self.assertFalse(output.exists())

    def test_loop_allows_cyclic_keyframe_brackets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            by_id = {frame["id"]: frame for frame in request["clips"][0]["frames"]}
            by_id["i1"].update(previous_keyframe="k3", next_keyframe="k0")
            by_id["i2"].update(previous_keyframe="k3", next_keyframe="k0")
            request["clips"][0]["frames"] = [by_id["i1"], by_id["k0"], by_id["k3"], by_id["i2"]]
            request["clips"][0]["loop"] = True
            request["reviews"][2]["subject_ids"] = ["canonical", "i1", "k0", "k3", "i2"]
            request["reviews"][2]["subject_sha256"] = {
                frame_id: request["reviews"][2]["subject_sha256"][frame_id]
                for frame_id in ("canonical", "i1", "k0", "k3", "i2")
            }
            self.write_json(request_path, request)
            output = root / "package"

            result = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
