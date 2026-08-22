from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).parents[1] / "scripts" / "spritesheet_pipeline.py"
sys.path.insert(0, str(SCRIPT.parent))

from spritesheet_core.rendering import apply_outline


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

    @staticmethod
    def reference_premultiplied_resize(
        image: Image.Image,
        size: tuple[int, int],
    ) -> Image.Image:
        rgba = np.asarray(image, dtype=np.float32) / 255.0
        alpha = rgba[..., 3:4]
        premultiplied = np.concatenate((rgba[..., :3] * alpha, alpha), axis=2)
        resized = np.stack(
            [
                np.asarray(
                    Image.fromarray(premultiplied[..., channel], "F").resize(
                        size,
                        Image.Resampling.LANCZOS,
                    ),
                    dtype=np.float32,
                )
                for channel in range(4)
            ],
            axis=2,
        )
        resized_alpha = np.rint(np.clip(resized[..., 3:4], 0.0, 1.0) * 255.0) / 255.0
        premultiplied_rgb = np.minimum(np.clip(resized[..., :3], 0.0, 1.0), resized_alpha)
        rgb = np.divide(
            premultiplied_rgb,
            resized_alpha,
            out=np.zeros_like(premultiplied_rgb),
            where=resized_alpha > 1e-6,
        )
        return Image.fromarray(
            np.rint(np.concatenate((rgb, resized_alpha), axis=2) * 255.0).astype(np.uint8),
            "RGBA",
        )

    @staticmethod
    def reference_outline(image: Image.Image, width: int, color: tuple[int, int, int, int]) -> Image.Image:
        seed = np.asarray(image.getchannel("A")) == 255
        padded = np.pad(seed, 1, constant_values=False)
        interior = (
            seed
            & padded[:-2, 1:-1]
            & padded[2:, 1:-1]
            & padded[1:-1, :-2]
            & padded[1:-1, 2:]
        )
        boundary_coordinates = np.argwhere(seed & ~interior)
        coverage = np.zeros(seed.shape, dtype=np.uint8)
        if boundary_coordinates.size:
            outer_radius = width + 1
            top = max(0, int(boundary_coordinates[:, 0].min()) - outer_radius)
            bottom = min(seed.shape[0], int(boundary_coordinates[:, 0].max()) + outer_radius + 1)
            left = max(0, int(boundary_coordinates[:, 1].min()) - outer_radius)
            right = min(seed.shape[1], int(boundary_coordinates[:, 1].max()) + outer_radius + 1)
            y_coordinates, x_coordinates = np.indices((bottom - top, right - left))
            y_coordinates += top
            x_coordinates += left
            squared_distance = np.full(y_coordinates.shape, np.iinfo(np.int64).max, dtype=np.int64)
            for boundary_y, boundary_x in boundary_coordinates:
                candidate_distance = (
                    (y_coordinates - int(boundary_y)) ** 2
                    + (x_coordinates - int(boundary_x)) ** 2
                )
                np.minimum(squared_distance, candidate_distance, out=squared_distance)

            cropped_coverage = np.zeros(squared_distance.shape, dtype=np.uint8)
            cropped_coverage[squared_distance <= width**2] = 255
            ramp = (squared_distance > width**2) & (squared_distance < outer_radius**2)
            fixed_one = 1 << 16
            for y, x in np.argwhere(ramp):
                fixed_distance = math.isqrt(int(squared_distance[y, x]) << 32)
                numerator = (outer_radius * fixed_one - fixed_distance) * 255
                quotient, remainder = divmod(numerator, fixed_one)
                doubled = remainder * 2
                if doubled > fixed_one or (
                    doubled == fixed_one and quotient % 2 == 1
                ):
                    quotient += 1
                cropped_coverage[y, x] = quotient
            coverage[top:bottom, left:right] = cropped_coverage
        coverage[seed] = 0
        if color[3] != 255:
            coverage = np.rint(coverage.astype(np.float64) * color[3] / 255).astype(np.uint8)

        ring = Image.fromarray(coverage, "L")
        outlined = Image.new("RGBA", image.size, color)
        outlined.putalpha(ring)
        outlined.alpha_composite(image)
        pixels = np.asarray(outlined).copy()
        pixels[..., :3][pixels[..., 3] == 0] = 0
        return Image.fromarray(pixels, "RGBA")

    def test_outline_uses_euclidean_coverage_instead_of_square_dilation(self) -> None:
        size = 512
        center = 256
        radius = 96
        y_coordinates, x_coordinates = np.indices((size, size))
        source_mask = (
            (x_coordinates - center) ** 2 + (y_coordinates - center) ** 2
            <= radius**2
        )
        source_pixels = np.zeros((size, size, 4), dtype=np.uint8)
        source_pixels[source_mask] = (180, 100, 60, 255)
        source = Image.fromarray(source_pixels, "RGBA")

        outlined, resolved_width = apply_outline(
            source,
            target_width=2,
            target_short_side=128,
            color=[0, 0, 0, 255],
        )
        outlined_alpha = np.asarray(outlined.getchannel("A"))

        diagonal_offset = 74
        diagonal_distance = (2 * diagonal_offset**2) ** 0.5
        self.assertGreater(diagonal_distance, radius + resolved_width + 0.5)
        diagonal_alpha = int(
            outlined_alpha[center + diagonal_offset, center + diagonal_offset]
        )
        partial_alpha_pixels = int(
            np.count_nonzero((outlined_alpha > 0) & (outlined_alpha < 255))
        )

        self.assertEqual(
            (resolved_width, diagonal_alpha, partial_alpha_pixels > 0),
            (8, 0, True),
            "a 2 px native outline must resolve to an 8 px Euclidean band with "
            "partial-alpha outer coverage, not a square 8 px dilation",
        )

    def test_outline_is_equivariant_under_exact_reflection_and_transpose(self) -> None:
        source = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        draw = ImageDraw.Draw(source)
        draw.polygon(
            ((19, 71), (29, 24), (47, 13), (76, 35), (68, 73), (38, 82)),
            fill=(180, 100, 60, 255),
        )
        transforms = (
            Image.Transpose.FLIP_LEFT_RIGHT,
            Image.Transpose.TRANSPOSE,
        )

        baseline, baseline_width = apply_outline(
            source,
            target_width=2,
            target_short_side=128,
            color=[7, 8, 9, 255],
        )

        for transform in transforms:
            with self.subTest(transform=transform):
                transformed, resolved_width = apply_outline(
                    source.transpose(transform),
                    target_width=2,
                    target_short_side=128,
                    color=[7, 8, 9, 255],
                )
                self.assertEqual(resolved_width, baseline_width)
                self.assertEqual(
                    transformed.tobytes(),
                    baseline.transpose(transform).tobytes(),
                    "Euclidean coverage must not become thicker along a reflected or "
                    "transposed silhouette direction",
                )

    def test_outline_is_byte_identical_across_repeated_application(self) -> None:
        source = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        ImageDraw.Draw(source).polygon(
            ((18, 74), (31, 19), (73, 28), (79, 67), (46, 83)),
            fill=(180, 100, 60, 255),
        )

        first, first_width = apply_outline(
            source,
            target_width=2,
            target_short_side=128,
            color=[7, 8, 9, 255],
        )
        second, second_width = apply_outline(
            source,
            target_width=2,
            target_short_side=128,
            color=[7, 8, 9, 255],
        )

        self.assertEqual((second_width, second.tobytes()), (first_width, first.tobytes()))

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
            {"id": "k0", "role": "keyframe", "source_path": str(frame_paths["k0"])},
            {
                "id": "i1",
                "role": "in-between",
                "source_path": str(frame_paths["i1"]),
                "previous_keyframe": "k0",
                "next_keyframe": "k3",
            },
            {
                "id": "i2",
                "role": "in-between",
                "source_path": str(frame_paths["i2"]),
                "previous_keyframe": "k0",
                "next_keyframe": "k3",
            },
            {"id": "k3", "role": "keyframe", "source_path": str(frame_paths["k3"])},
        ]
        request_data: dict[str, object] = {
            "schema_version": "spritesheet-production-request/v4",
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

    def enable_outline_for_production_request(
        self,
        root: Path,
        request: dict[str, object],
        outline: dict[str, object],
    ) -> None:
        canonical_source = root / "canonical-outlined-source.png"
        source_image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        ImageDraw.Draw(source_image).rectangle((100, 80, 299, 319), fill=(120, 80, 40, 255))
        source_image.save(canonical_source)
        canonical_request = root / "canonical-outlined-authoring.json"
        self.write_json(
            canonical_request,
            {
                "schema_version": "canonical-authoring-request/v3",
                "canonical_id": "canonical",
                "source": str(canonical_source),
                "target": {"frame_width": 32, "frame_height": 32},
                "outline": outline,
            },
        )
        canonical_output = root / "canonical-outlined-prepared"
        prepared = self.run_cli(
            "prepare-canonical",
            "--request",
            str(canonical_request),
            "--output-dir",
            str(canonical_output),
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        canonical = canonical_output / "canonical-reference-candidate.png"
        evidence = canonical_output / "canonical-reference-evidence.json"
        proof = canonical_output / "canonical-admission-proof.json"
        request["contract"]["outline"] = outline
        request["canonical_references"][0] = {
            "id": "canonical",
            "path": str(canonical),
            "evidence_path": str(evidence),
            "proof_path": str(proof),
        }
        canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
        admission_hash = hashlib.sha256(proof.read_bytes()).hexdigest()
        frame_hashes: dict[str, str] = {}
        for index, frame in enumerate(request["clips"][0]["frames"], start=1):
            source_path = Path(frame["source_path"])
            source = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle(
                (160 + index, 128, 351 + index, 383),
                fill=(40 + index, 90, 140, 255),
            )
            source.save(source_path)
            frame_hashes[frame["id"]] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        for review in request["reviews"]:
            review["subject_sha256"]["canonical"] = canonical_hash
            review["admission_sha256"]["canonical"] = admission_hash
            for subject_id in review["subject_ids"]:
                if subject_id in frame_hashes:
                    review["subject_sha256"][subject_id] = frame_hashes[subject_id]

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

    def test_build_rejects_legacy_shaped_v3_evidence_and_v1_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 1, "color": [0, 0, 0, 255]}
            self.enable_outline_for_production_request(root, request, outline)
            evidence_path = Path(request["canonical_references"][0]["evidence_path"])
            proof_path = Path(request["canonical_references"][0]["proof_path"])
            evidence = json.loads(evidence_path.read_text())
            evidence.pop("alpha_policy")
            evidence.pop("review_previews")
            evidence["derivation"]["outline"] = "outward-silhouette-maxfilter/v1"
            evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
            proof = json.loads(proof_path.read_text())
            proof.pop("alpha_policy")
            proof.pop("review_previews")
            proof["derivation"]["outline"] = "outward-silhouette-maxfilter/v1"
            proof["authoring_evidence_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            proof_path.write_text(json.dumps(proof, indent=2) + "\n")
            proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                review["admission_sha256"]["canonical"] = proof_hash
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(built.returncode, 1)
            self.assertIn("missing required fields", built.stdout)
            self.assertFalse(output.exists())

    def test_build_rejects_current_admission_with_legacy_outline_algorithm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 1, "color": [0, 0, 0, 255]}
            self.enable_outline_for_production_request(root, request, outline)
            evidence_path = Path(request["canonical_references"][0]["evidence_path"])
            proof_path = Path(request["canonical_references"][0]["proof_path"])
            legacy_algorithm = "outward-silhouette-maxfilter-opaque-alpha/v2"

            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["derivation"]["outline"] = legacy_algorithm
            evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            evidence_hash = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            proof["derivation"]["outline"] = legacy_algorithm
            proof["authoring_evidence_sha256"] = evidence_hash
            proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                review["admission_sha256"]["canonical"] = proof_hash
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli(
                "build-package",
                "--request",
                str(request_path),
                "--output-dir",
                str(output),
            )

            self.assertEqual(built.returncode, 1)
            self.assertIn("derivation algorithms", built.stdout)
            self.assertFalse(output.exists())

    def test_verify_rejects_legacy_shaped_current_package_admission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            admission = manifest["canonical_admissions"][0]
            evidence_path = output / admission["evidence_path"]
            evidence = json.loads(evidence_path.read_text())
            evidence.pop("alpha_policy")
            evidence.pop("review_previews")
            evidence_bytes = (json.dumps(evidence, indent=2) + "\n").encode()
            evidence_hash = hashlib.sha256(evidence_bytes).hexdigest()
            new_evidence_path = output / "evidence" / f"{evidence_hash}.json"
            new_evidence_path.write_bytes(evidence_bytes)
            evidence_path.unlink()
            proof_path = output / admission["proof_path"]
            proof = json.loads(proof_path.read_text())
            proof.pop("alpha_policy")
            proof.pop("review_previews")
            proof["authoring_evidence_sha256"] = evidence_hash
            proof_bytes = (json.dumps(proof, indent=2) + "\n").encode()
            proof_hash = hashlib.sha256(proof_bytes).hexdigest()
            new_proof_path = output / "admission" / f"{proof_hash}.json"
            new_proof_path.write_bytes(proof_bytes)
            proof_path.unlink()
            admission.update(
                evidence_path=f"evidence/{evidence_hash}.json",
                evidence_sha256=evidence_hash,
                proof_path=f"admission/{proof_hash}.json",
                proof_sha256=proof_hash,
            )
            for review in manifest["reviews"]:
                review["admission_sha256"]["canonical"] = proof_hash
            manifest["rendering"]["mask_policy"] = "nonzero-alpha/v1"
            manifest_path.write_text(json.dumps(manifest))

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("missing required fields", verified.stdout)

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
                {
                    "canonical-reference-candidate.png",
                    record["source"]["path"],
                    *[preview["path"] for preview in record["review_previews"]],
                },
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

    def test_prepare_canonical_binds_alpha_policy_and_dual_size_background_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((127, 127, 384, 384), outline=(245, 245, 245, 8), width=2)
            draw.rectangle((129, 129, 382, 382), fill=(120, 80, 40, 255))
            image.save(source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 128, "frame_height": 128},
                    "outline": {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads((output / "canonical-reference-evidence.json").read_text(encoding="utf-8"))
            alpha = evidence["alpha_policy"]
            self.assertEqual(
                alpha,
                {
                    "boundary_check": "exterior-low-alpha-boundary/v1",
                    "low_alpha_threshold": 16,
                    "outline_mask": "opaque-alpha-threshold/v1",
                    "outline_alpha_threshold": 255,
                    "source_low_alpha_boundary_pixels": alpha["source_low_alpha_boundary_pixels"],
                    "source_partial_alpha_boundary_pixels": alpha["source_partial_alpha_boundary_pixels"],
                    "unbacked_source_boundary_pixels": 0,
                    "status": "passed",
                },
            )
            self.assertGreater(alpha["source_low_alpha_boundary_pixels"], 0)
            self.assertGreaterEqual(
                alpha["source_partial_alpha_boundary_pixels"],
                alpha["source_low_alpha_boundary_pixels"],
            )
            expected_matrix = {
                ("high-resolution", "white", 512, 512),
                ("high-resolution", "dark", 512, 512),
                ("high-resolution", "checkerboard", 512, 512),
                ("native", "white", 128, 128),
                ("native", "dark", 128, 128),
                ("native", "checkerboard", 128, 128),
            }
            actual_matrix = set()
            for record in evidence["review_previews"]:
                preview = output / record["path"]
                self.assertTrue(preview.is_file())
                self.assertEqual(record["sha256"], hashlib.sha256(preview.read_bytes()).hexdigest())
                with Image.open(preview) as opened:
                    self.assertEqual(opened.mode, "RGBA")
                    self.assertEqual(opened.size, (record["width"], record["height"]))
                actual_matrix.add(
                    (record["scale"], record["background"], record["width"], record["height"]),
                )
            self.assertEqual(actual_matrix, expected_matrix)
            proof = json.loads((output / "canonical-admission-proof.json").read_text(encoding="utf-8"))
            self.assertEqual(proof["alpha_policy"], alpha)
            self.assertEqual(proof["review_previews"], evidence["review_previews"])

    def test_prepare_rejects_unbacked_low_alpha_fringe_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((96, 96, 415, 415), outline=(255, 255, 255, 32), width=2)
            draw.rectangle((160, 160, 351, 351), fill=(120, 80, 40, 255))
            image.save(source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 128, "frame_height": 128},
                    "outline": {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 1)
            self.assertIn("unbacked low-alpha boundary", result.stdout)
            self.assertFalse(output.exists())

    def test_prepare_rejects_close_partial_fringe_outside_actual_outline_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((150, 150, 361, 361), outline=(255, 255, 255, 32), width=1)
            draw.rectangle((160, 160, 351, 351), fill=(120, 80, 40, 255))
            image.save(source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 128, "frame_height": 128},
                    "outline": {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]},
                },
            )
            output = root / "canonical"

            result = self.run_cli("prepare-canonical", "--request", str(request), "--output-dir", str(output))

            self.assertEqual(result.returncode, 1)
            self.assertIn("unbacked low-alpha boundary", result.stdout)
            self.assertFalse(output.exists())

    def test_prepare_rechecks_partial_boundary_exposed_by_low_alpha_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((96, 96, 415, 415), fill=(255, 255, 255, 8))
            draw.rectangle((100, 100, 411, 411), fill=(255, 255, 255, 17))
            draw.rectangle((160, 160, 351, 351), fill=(120, 80, 40, 255))
            image.save(source)
            request = root / "request.json"
            self.write_json(
                request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": {
                        "enabled": True,
                        "target_width": 2,
                        "color": [7, 8, 9, 255],
                    },
                },
            )
            output = root / "canonical"

            result = self.run_cli(
                "prepare-canonical",
                "--request",
                str(request),
                "--output-dir",
                str(output),
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("unbacked low-alpha boundary", result.stdout)
            self.assertFalse(output.exists())

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
            self.assertIn("color alpha must be 255", result.stdout)
            self.assertFalse(output.exists())

    def test_prepare_rejects_nonopaque_enabled_outline_color_atomically(self) -> None:
        for alpha in (1, 254):
            with self.subTest(alpha=alpha), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "source.png"
                source_image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
                ImageDraw.Draw(source_image).rectangle(
                    (160, 128, 351, 383),
                    fill=(120, 80, 40, 255),
                )
                source_image.save(source)
                request = root / "request.json"
                self.write_json(
                    request,
                    {
                        "schema_version": "canonical-authoring-request/v3",
                        "canonical_id": "canonical",
                        "source": str(source),
                        "target": {"frame_width": 32, "frame_height": 32},
                        "outline": {
                            "enabled": True,
                            "target_width": 2,
                            "color": [7, 8, 9, alpha],
                        },
                    },
                )
                output = root / "canonical"

                rejected = self.run_cli(
                    "prepare-canonical",
                    "--request",
                    str(request),
                    "--output-dir",
                    str(output),
                )

                self.assertEqual(rejected.returncode, 1)
                self.assertIn("color alpha must be 255", rejected.stdout)
                self.assertFalse(output.exists())

    def test_build_rejects_nonopaque_enabled_outline_color_atomically(self) -> None:
        for alpha in (1, 254):
            with self.subTest(alpha=alpha), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                outline = {
                    "enabled": True,
                    "target_width": 2,
                    "color": [7, 8, 9, 255],
                }
                self.enable_outline_for_production_request(root, request, outline)
                request["contract"]["outline"]["color"][3] = alpha
                self.write_json(request_path, request)
                output = root / "package"

                rejected = self.run_cli(
                    "build-package",
                    "--request",
                    str(request_path),
                    "--output-dir",
                    str(output),
                )

                self.assertEqual(rejected.returncode, 1)
                self.assertIn("color alpha must be 255", rejected.stdout)
                self.assertFalse(output.exists())

    def test_build_rejects_outlined_frame_without_opaque_silhouette_seed_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {
                "enabled": True,
                "target_width": 2,
                "color": [7, 8, 9, 255],
            }
            self.enable_outline_for_production_request(root, request, outline)
            frame = request["clips"][0]["frames"][0]
            frame_path = Path(frame["source_path"])
            source = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            ImageDraw.Draw(source).rectangle(
                (160, 128, 351, 383),
                fill=(120, 80, 40, 254),
            )
            source.save(frame_path)
            frame_hash = hashlib.sha256(frame_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                if frame["id"] in review["subject_ids"]:
                    review["subject_sha256"][frame["id"]] = frame_hash
            self.write_json(request_path, request)
            output = root / "package"

            rejected = self.run_cli(
                "build-package",
                "--request",
                str(request_path),
                "--output-dir",
                str(output),
            )

            self.assertEqual(rejected.returncode, 1)
            self.assertIn("opaque silhouette seed", rejected.stdout)
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

    def test_outline_preserves_opaque_pixels_and_backs_partial_boundary_pixels(self) -> None:
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
                if plain_pixel[3] == 255:
                    self.assertEqual(plain_pixel, outlined_pixel)
            partial_index = next(index for index, pixel in enumerate(plain_pixels) if pixel[3] == 128)
            self.assertEqual(outlined_pixels[partial_index][3], 255)
            self.assertNotEqual(outlined_pixels[partial_index], plain_pixels[partial_index])

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
            self.assertGreater(evidence["alpha_policy"]["source_low_alpha_boundary_pixels"], 0)
            self.assertEqual(evidence["alpha_policy"]["unbacked_source_boundary_pixels"], 0)
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
                plain_bbox = plain_image.getchannel("A").point(
                    lambda value: 255 if value == 255 else 0,
                ).getbbox()
                candidate_bbox = candidate.getchannel("A").point(
                    lambda value: 255 if value == 255 else 0,
                ).getbbox()
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
            self.assertEqual(manifest["schema_version"], "spritesheet-package/v4")
            self.assertEqual(len(manifest["canonical_admissions"]), 1)
            admission = manifest["canonical_admissions"][0]
            self.assertTrue((output / admission["proof_path"]).is_file())
            self.assertNotIn("witness_path", admission)
            self.assertEqual(
                {artifact["type"] for artifact in manifest["artifacts"]},
                {"canonical-reference", "high-resolution-frame-source", "spritesheet"},
            )
            frame_artifacts = [
                artifact
                for artifact in manifest["artifacts"]
                if artifact["type"] == "high-resolution-frame-source"
            ]
            self.assertEqual([frame["role"] for frame in frame_artifacts], ["keyframe", "in-between", "in-between", "keyframe"])
            self.assertEqual(manifest["clips"][0]["frame_ids"], ["k0", "i1", "i2", "k3"])
            self.assertEqual(manifest["clips"][0]["durations_ms"], [100, 100, 100, 100])
            self.assertEqual(manifest["contract"]["anchor"], [16, 31])
            rendering = manifest["rendering"]
            self.assertEqual(
                set(rendering),
                {
                    "schema_version",
                    "pixel_protocol_id",
                    "pipeline",
                    "mask_policy",
                    "outline_algorithm",
                    "sampler",
                    "resolved_high_resolution_outline_width",
                    "frames",
                    "sheet_rgba_sha256",
                },
            )
            self.assertEqual(rendering["schema_version"], "spritesheet-rendering-receipt/v2")
            self.assertEqual(
                rendering["pixel_protocol_id"],
                "smooth-raster-pixel-protocol/v3",
            )
            self.assertEqual(rendering["outline_algorithm"], "identity/v1")
            self.assertEqual(rendering["resolved_high_resolution_outline_width"], 0)
            self.assertEqual([frame["source"] for frame in rendering["frames"]], ["k0", "i1", "i2", "k3"])
            request_data = json.loads(request.read_text(encoding="utf-8"))
            first_source_path = Path(request_data["clips"][0]["frames"][0]["source_path"])
            with Image.open(first_source_path) as first_source:
                first_source_rgba_sha256 = hashlib.sha256(first_source.convert("RGBA").tobytes()).hexdigest()
            self.assertEqual(
                rendering["frames"][0]["outlined_rgba_sha256"],
                first_source_rgba_sha256,
            )
            serialized = manifest_path.read_text(encoding="utf-8").lower()
            self.assertNotIn("target-frame", serialized)
            self.assertNotIn("target.png", serialized)
            self.assertEqual(list(output.rglob("*target*.png")), [])
            self.assertEqual(list(output.rglob("*outlined*.png")), [])

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            self.assertIn("PASS MACHINE-VERIFIED rendering", verified.stdout)
            self.assertIn("INFO REVIEWED canonical-approval", verified.stdout)

    def test_build_renders_high_resolution_outline_before_target_resize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]}

            canonical_source = root / "outlined-canonical-source.png"
            canonical_image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            ImageDraw.Draw(canonical_image).rectangle((96, 72, 303, 327), fill=(120, 80, 40, 255))
            canonical_image.save(canonical_source)
            canonical_request = root / "outlined-canonical-request.json"
            self.write_json(
                canonical_request,
                {
                    "schema_version": "canonical-authoring-request/v3",
                    "canonical_id": "canonical",
                    "source": str(canonical_source),
                    "target": {"frame_width": 32, "frame_height": 32},
                    "outline": outline,
                },
            )
            canonical_output = root / "outlined-canonical"
            prepared = self.run_cli(
                "prepare-canonical",
                "--request",
                str(canonical_request),
                "--output-dir",
                str(canonical_output),
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            canonical = canonical_output / "canonical-reference-candidate.png"
            canonical_evidence = canonical_output / "canonical-reference-evidence.json"
            canonical_proof = canonical_output / "canonical-admission-proof.json"

            for index, frame in enumerate(request["clips"][0]["frames"], start=1):
                source_path = Path(frame["source_path"])
                source = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
                ImageDraw.Draw(source).rectangle(
                    (176 + index, 128, 335 + index, 383),
                    fill=(40 + index, 90, 140, 255),
                )
                source.save(source_path)

            request["contract"]["outline"] = outline
            request["canonical_references"][0] = {
                "id": "canonical",
                "path": str(canonical),
                "evidence_path": str(canonical_evidence),
                "proof_path": str(canonical_proof),
            }
            canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
            admission_hash = hashlib.sha256(canonical_proof.read_bytes()).hexdigest()
            frame_hashes = {
                frame["id"]: hashlib.sha256(Path(frame["source_path"]).read_bytes()).hexdigest()
                for frame in request["clips"][0]["frames"]
            }
            for review in request["reviews"]:
                review["subject_sha256"]["canonical"] = canonical_hash
                review["admission_sha256"]["canonical"] = admission_hash
                for subject_id in review["subject_ids"]:
                    if subject_id in frame_hashes:
                        review["subject_sha256"][subject_id] = frame_hashes[subject_id]
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            first_source = Image.open(request["clips"][0]["frames"][0]["source_path"]).convert("RGBA")
            outlined_high_resolution = self.reference_outline(first_source, 32, (7, 8, 9, 255))
            expected_cell = self.reference_premultiplied_resize(outlined_high_resolution, (32, 32))
            raw_target = self.reference_premultiplied_resize(first_source, (32, 32))
            illegal_target_postprocess = self.reference_outline(raw_target, 2, (7, 8, 9, 255))
            with Image.open(output / "spritesheet.png") as sheet:
                first_cell = sheet.crop((0, 0, 32, 32)).convert("RGBA")
            self.assertEqual(first_cell.tobytes(), expected_cell.tobytes())
            self.assertNotEqual(first_cell.tobytes(), raw_target.tobytes())
            self.assertNotEqual(first_cell.tobytes(), illegal_target_postprocess.tobytes())
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            rendered = manifest["rendering"]
            self.assertEqual(rendered["schema_version"], "spritesheet-rendering-receipt/v2")
            self.assertEqual(
                rendered["outline_algorithm"],
                "outward-silhouette-euclidean-coverage-opaque-alpha/v3",
            )
            self.assertEqual(rendered["resolved_high_resolution_outline_width"], 32)
            self.assertEqual(
                rendered["frames"][0]["outlined_rgba_sha256"],
                hashlib.sha256(outlined_high_resolution.tobytes()).hexdigest(),
            )
            self.assertEqual(
                rendered["frames"][0]["cell_rgba_sha256"],
                hashlib.sha256(expected_cell.tobytes()).hexdigest(),
            )
            colors = first_cell.getcolors(maxcolors=first_cell.width * first_cell.height)
            self.assertGreater(
                sum(
                    count
                    for count, pixel in colors or []
                    if pixel[:3] == (7, 8, 9) and pixel[3] > 0
                ),
                0,
            )

    def test_verify_rejects_tampered_rendering_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["rendering"]["frames"][0]["outlined_rgba_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED rendering", verified.stdout)

    def test_verify_rejects_missing_or_tampered_receipt_pixel_protocol(self) -> None:
        mutations = {
            "missing": lambda rendering: rendering.pop("pixel_protocol_id"),
            "tampered": lambda rendering: rendering.update(
                pixel_protocol_id="smooth-raster-pixel-protocol/v2",
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request, _ = self.make_production_request(root)
                output = root / "package"
                built = self.run_cli(
                    "build-package",
                    "--request",
                    str(request),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                manifest_path = output / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                rendering = manifest["rendering"]
                rendering["pixel_protocol_id"] = "smooth-raster-pixel-protocol/v3"
                mutate(rendering)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                verified = self.run_cli(
                    "verify-package",
                    "--manifest",
                    str(manifest_path),
                )

                self.assertEqual(verified.returncode, 1)
                self.assertIn("FAIL MACHINE-VERIFIED rendering", verified.stdout)

    def test_verify_rejects_legacy_rendering_receipt_schema_and_outline_algorithm(self) -> None:
        mutations = {
            "receipt-schema": lambda rendering: rendering.update(
                schema_version="spritesheet-rendering-receipt/v1",
            ),
            "outline-algorithm": lambda rendering: rendering.update(
                outline_algorithm="outward-silhouette-maxfilter-opaque-alpha/v2",
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                outline = {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]}
                self.enable_outline_for_production_request(root, request, outline)
                self.write_json(request_path, request)
                output = root / "package"
                built = self.run_cli(
                    "build-package",
                    "--request",
                    str(request_path),
                    "--output-dir",
                    str(output),
                )
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                manifest_path = output / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest["rendering"])
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

                self.assertEqual(verified.returncode, 1)
                self.assertIn("FAIL MACHINE-VERIFIED rendering", verified.stdout)

    def test_verify_rejects_sheet_built_by_resizing_raw_sources_without_outline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]}
            self.enable_outline_for_production_request(root, request, outline)
            self.write_json(request_path, request)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sheet_path = output / "spritesheet.png"
            with Image.open(sheet_path) as opened:
                sheet = Image.new("RGBA", opened.size, (0, 0, 0, 0))
            for cell in manifest["assembly"]["cells"]:
                artifact = next(item for item in manifest["artifacts"] if item["id"] == cell["source"])
                with Image.open(output / artifact["path"]) as source:
                    raw_cell = source.convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
                sheet.alpha_composite(raw_cell, (cell["column"] * 32, cell["row"] * 32))
            sheet.save(sheet_path)
            sheet_artifact = next(item for item in manifest["artifacts"] if item["id"] == "spritesheet")
            sheet_artifact["sha256"] = hashlib.sha256(sheet_path.read_bytes()).hexdigest()
            manifest["rendering"]["sheet_rgba_sha256"] = hashlib.sha256(sheet.tobytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED cells", verified.stdout)

    def test_build_rejects_outline_when_rendered_source_would_touch_border_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            outline = {"enabled": True, "target_width": 2, "color": [7, 8, 9, 255]}
            self.enable_outline_for_production_request(root, request, outline)
            first_frame = request["clips"][0]["frames"][0]
            first_path = Path(first_frame["source_path"])
            clipped = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            ImageDraw.Draw(clipped).rectangle((4, 128, 255, 383), fill=(100, 90, 80, 255))
            clipped.save(first_path)
            changed_hash = hashlib.sha256(first_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                if first_frame["id"] in review["subject_ids"]:
                    review["subject_sha256"][first_frame["id"]] = changed_hash
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(built.returncode, 1)
            self.assertIn("must not touch the canvas border", built.stdout)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".package-*")), [])

    def test_build_rejects_v1_and_invalid_graphs_without_partial_output(self) -> None:
        mutations = {
            "v1": lambda request: request.update(schema_version="spritesheet-production-request/v1"),
            "v3": lambda request: request.update(schema_version="spritesheet-production-request/v3"),
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
            first = Path(request["clips"][0]["frames"][0]["source_path"])
            second = Path(request["clips"][0]["frames"][1]["source_path"])
            second.write_bytes(first.read_bytes())
            output = root / "duplicate"

            duplicate = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(duplicate.returncode, 1)
            self.assertIn("distinct pixels", duplicate.stdout)
            self.assertFalse(output.exists())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            changed = Path(request["clips"][0]["frames"][2]["source_path"])
            self.write_rgba(changed, (512, 512), 99)
            output = root / "changed"

            stale_review = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(stale_review.returncode, 1)
            self.assertIn("subject_sha256", stale_review.stdout)
            self.assertFalse(output.exists())

    def test_repeat_opening_cell_reuses_first_pixels_without_a_second_receipt_record(self) -> None:
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
            self.assertEqual(len(manifest["rendering"]["frames"]), 4)
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

    def test_verify_rejects_transparent_rgb_tampering_in_unused_cell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root, columns=3)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            sheet_path = output / "spritesheet.png"
            with Image.open(sheet_path) as opened:
                sheet = opened.copy()
            sheet.putpixel((65, 33), (1, 2, 3, 0))
            sheet.save(sheet_path)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            sheet_record = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "spritesheet")
            sheet_record["sha256"] = hashlib.sha256(sheet_path.read_bytes()).hexdigest()
            manifest["rendering"]["sheet_rgba_sha256"] = hashlib.sha256(sheet.tobytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            verified = self.run_cli("verify-package", "--manifest", str(manifest_path))

            self.assertEqual(verified.returncode, 1)
            self.assertIn("FAIL MACHINE-VERIFIED sheet.replay", verified.stdout)

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
            "alpha-threshold": lambda evidence: evidence["alpha_policy"].update(low_alpha_threshold=17),
            "preview-hash": lambda evidence: evidence["review_previews"][0].update(sha256="0" * 64),
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

    def test_build_rejects_tampered_canonical_review_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            evidence_path = Path(request["canonical_references"][0]["evidence_path"])
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            preview_path = evidence_path.parent / evidence["review_previews"][0]["path"]
            with Image.open(preview_path) as opened:
                preview = opened.copy()
            preview.putpixel((0, 0), (1, 2, 3, 255))
            preview.save(preview_path)
            output = root / "package"

            rejected = self.run_cli("build-package", "--request", str(request_path), "--output-dir", str(output))

            self.assertEqual(rejected.returncode, 1)
            self.assertFalse(output.exists())

    def test_build_accepts_review_previews_reencoded_with_identical_rgba(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path, request = self.make_production_request(root)
            canonical = request["canonical_references"][0]
            evidence_path = Path(canonical["evidence_path"])
            proof_path = Path(canonical["proof_path"])
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

            for record in evidence["review_previews"]:
                preview_path = evidence_path.parent / record["path"]
                original_png_hash = hashlib.sha256(preview_path.read_bytes()).hexdigest()
                with Image.open(preview_path) as opened:
                    preview = opened.convert("RGBA")
                    original_rgba_hash = hashlib.sha256(preview.tobytes()).hexdigest()
                preview.save(preview_path, format="PNG", compress_level=0)
                reencoded_png_hash = hashlib.sha256(preview_path.read_bytes()).hexdigest()
                with Image.open(preview_path) as opened:
                    reencoded_rgba_hash = hashlib.sha256(
                        opened.convert("RGBA").tobytes(),
                    ).hexdigest()
                self.assertNotEqual(reencoded_png_hash, original_png_hash)
                self.assertEqual(reencoded_rgba_hash, original_rgba_hash)
                self.assertEqual(record["rgba_sha256"], original_rgba_hash)
                record["sha256"] = reencoded_png_hash

            evidence_path.write_text(
                json.dumps(evidence, indent=2) + "\n",
                encoding="utf-8",
            )
            evidence_hash = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            proof["review_previews"] = evidence["review_previews"]
            proof["authoring_evidence_sha256"] = evidence_hash
            proof_path.write_text(
                json.dumps(proof, indent=2) + "\n",
                encoding="utf-8",
            )
            proof_hash = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                review["admission_sha256"]["canonical"] = proof_hash
            self.write_json(request_path, request)
            output = root / "package"

            built = self.run_cli(
                "build-package",
                "--request",
                str(request_path),
                "--output-dir",
                str(output),
            )
            verified = self.run_cli(
                "verify-package",
                "--manifest",
                str(output / "manifest.json"),
            )

            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_build_rejects_symlinked_canonical_frame_source_evidence_and_proof_inputs(self) -> None:
        for input_kind in ("canonical", "frame", "source", "evidence", "proof"):
            with self.subTest(input_kind=input_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request_path, request = self.make_production_request(root)
                canonical_entry = request["canonical_references"][0]
                if input_kind == "frame":
                    target = Path(request["clips"][0]["frames"][0]["source_path"])
                    field_owner = request["clips"][0]["frames"][0]
                    field = "source_path"
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
            frame_hashes: dict[str, str] = {}
            for index, frame in enumerate(request["clips"][0]["frames"], start=1):
                source_path = Path(frame["source_path"])
                source = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
                ImageDraw.Draw(source).rectangle(
                    (128 + index, 128, 383 + index, 383),
                    fill=(40 + index, 90, 140, 255),
                )
                source.save(source_path)
                frame_hashes[frame["id"]] = hashlib.sha256(source_path.read_bytes()).hexdigest()
            for review in request["reviews"]:
                review["subject_sha256"]["canonical"] = canonical_hash
                review["admission_sha256"]["canonical"] = admission_hash
                for subject_id in review["subject_ids"]:
                    if subject_id in frame_hashes:
                        review["subject_sha256"][subject_id] = frame_hashes[subject_id]
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

    def test_verify_hard_rejects_v3_and_canonical_as_a_frame_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request, _ = self.make_production_request(root)
            output = root / "package"
            built = self.run_cli("build-package", "--request", str(request), "--output-dir", str(output))
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["schema_version"] = "spritesheet-package/v3"
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
                frame = {"id": frame_id, "role": role, "source_path": str(path)}
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
                frame["id"]: hashlib.sha256(Path(frame["source_path"]).read_bytes()).hexdigest()
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
                frame["source_path"] = str(new_path)
            by_role = request["clips"][1]["frames"]
            for frame in by_role:
                if frame["role"] == "in-between":
                    frame["previous_keyframe"] = "second-k0"
                    frame["next_keyframe"] = "second-k3"
            request["contract"]["frame_count"] = 8
            hashes = {
                frame["id"]: hashlib.sha256(Path(frame["source_path"]).read_bytes()).hexdigest()
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
