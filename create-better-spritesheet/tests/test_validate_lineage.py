from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_lineage.py"


class ValidateLineageTests(unittest.TestCase):
    def write_image(self, root: Path, name: str, size: tuple[int, int], color: tuple[int, int, int, int]) -> dict[str, object]:
        path = root / f"{name}.png"
        image = Image.new("RGBA", size, color)
        image.save(path)
        artifact_type = {
            "pre": "high-resolution-pre-master",
            "master": "canonical-master",
            "k0": "high-resolution-keyframe",
            "k3": "high-resolution-keyframe",
            "i1": "high-resolution-in-between",
            "i2": "high-resolution-in-between",
            "sheet": "spritesheet",
        }.get(name, "target-frame")
        return {
            "id": name,
            "type": artifact_type,
            "path": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "width": size[0],
            "height": size[1],
            "mode": "RGBA",
        }

    def make_fixture(self, root: Path) -> Path:
        artifacts = [
            self.write_image(root, "pre", (512, 512), (1, 2, 3, 255)),
            self.write_image(root, "master", (512, 512), (1, 2, 3, 255)),
            self.write_image(root, "k0", (512, 512), (10, 20, 30, 255)),
            self.write_image(root, "i1", (512, 512), (20, 30, 40, 255)),
            self.write_image(root, "i2", (512, 512), (30, 40, 50, 255)),
            self.write_image(root, "k3", (512, 512), (40, 50, 60, 255)),
        ]
        colors = [
            (100, 0, 0, 255),
            (0, 100, 0, 255),
            (0, 0, 100, 255),
            (100, 100, 0, 255),
        ]
        for index, color in enumerate(colors):
            artifacts.append(self.write_image(root, f"t{index}", (4, 4), color))
        sheet = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for index, color in enumerate(colors):
            sheet.alpha_composite(Image.new("RGBA", (4, 4), color), ((index % 2) * 4, (index // 2) * 4))
        sheet_path = root / "sheet.png"
        sheet.save(sheet_path)
        artifacts.append(
            {
                "id": "sheet",
                "type": "spritesheet",
                "path": sheet_path.name,
                "sha256": hashlib.sha256(sheet_path.read_bytes()).hexdigest(),
                "width": 8,
                "height": 8,
                "mode": "RGBA",
            },
        )
        frames = [
            {"index": 0, "role": "keyframe", "high_resolution": "k0", "target": "t0"},
            {
                "index": 1,
                "role": "in-between",
                "high_resolution": "i1",
                "target": "t1",
                "previous_keyframe": 0,
                "next_keyframe": 3,
            },
            {
                "index": 2,
                "role": "in-between",
                "high_resolution": "i2",
                "target": "t2",
                "previous_keyframe": 0,
                "next_keyframe": 3,
            },
            {"index": 3, "role": "keyframe", "high_resolution": "k3", "target": "t3"},
        ]
        manifest = {
            "schema_version": "spritesheet-lineage/v1",
            "contract": {
                "frame_width": 4,
                "frame_height": 4,
                "frame_count": 4,
                "canonical_short_side": 512,
                "outline": {"enabled": False, "target_width": "none"},
                "extension_field": "allowed",
            },
            "artifacts": artifacts,
            "relations": [
                {
                    "id": "lock-master",
                    "type": "canonical-lock",
                    "sources": ["pre"],
                    "target": "master",
                    "outline_enabled": False,
                    "outline_target_width": "none",
                },
                {"id": "reference-k0", "type": "canonical-reference", "sources": ["master"], "target": "k0"},
                {"id": "reference-k3", "type": "canonical-reference", "sources": ["master"], "target": "k3"},
                {"id": "bracket-i1", "type": "adjacent-keyframe-reference", "sources": ["k0", "k3"], "target": "i1"},
                {"id": "bracket-i2", "type": "adjacent-keyframe-reference", "sources": ["k0", "k3"], "target": "i2"},
            ],
            "clips": [
                {
                    "id": "action-east",
                    "loop": False,
                    "repeated_closing_target": False,
                    "frames": frames,
                },
            ],
            "reviews": [
                {
                    "id": f"review-{subject}",
                    "subject": subject,
                    "stage": {
                        "master": "canonical-lock",
                        "k0": "keyframe-approval",
                        "k3": "keyframe-approval",
                        "i1": "in-between-approval",
                        "i2": "in-between-approval",
                    }[subject],
                    "status": "approved",
                    "reviewer": "reviewer-1",
                    "declared_order": index + 1,
                }
                for index, subject in enumerate(("master", "k0", "k3", "i1", "i2"))
            ],
            "transforms": [
                {
                    "id": f"downsample-{index}",
                    "type": "downsample",
                    "source": source,
                    "target": f"t{index}",
                    "declared_resize_count": 1,
                    "declared_order": index + 6,
                }
                for index, source in enumerate(("k0", "i1", "i2", "k3"))
            ],
            "assembly": {
                "sheet": "sheet",
                "columns": 2,
                "rows": 2,
                "order": "row-major",
                "targets": ["t0", "t1", "t2", "t3"],
            },
            "unknown_root_field": {"allowed": True},
        }
        manifest_path = root / "lineage.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def run_validator(self, manifest: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--lineage", str(manifest)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_valid_fixture_passes_without_claiming_historical_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_validator(self.make_fixture(Path(directory)))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS MACHINE-VERIFIED assembly.targets[3].pixels", result.stdout)
        self.assertIn("INFO DECLARED transforms[0]", result.stdout)
        self.assertIn("actual transform count, order, and method are not recoverable from pixels", result.stdout)
        self.assertIn("INFO REVIEWED reviews[0]", result.stdout)
        self.assertIn("machine_failures=0", result.stdout)

    def test_tampered_target_fails_hash_and_sheet_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.make_fixture(root)
            Image.new("RGBA", (4, 4), (255, 0, 255, 255)).save(root / "t2.png")
            result = self.run_validator(manifest)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED artifacts[8].sha256", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED assembly.targets[2].pixels", result.stdout)

    def test_invalid_bracket_and_duplicate_downsample_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["clips"][0]["frames"][1]["next_keyframe"] = 2
            manifest["transforms"].append(dict(manifest["transforms"][0], id="duplicate-downsample"))
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].frame[index=1].bracketing", result.stdout)
        self.assertIn("declarations=2", result.stdout)

    def test_conflicting_extra_bracket_relation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["relations"].append(
                {
                    "id": "conflicting-bracket-i1",
                    "type": "adjacent-keyframe-reference",
                    "sources": ["k3", "k0"],
                    "target": "i1",
                },
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].frame[index=1].adjacent-keyframe-reference", result.stdout)
        self.assertIn("all target relations=2", result.stdout)

    def test_unhashable_json_values_fail_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"][0]["type"] = []
            manifest["relations"][0]["sources"] = [{}]
            manifest["relations"][1]["sources"] = [{}]
            manifest["clips"][0]["frames"][0]["target"] = {}
            manifest["assembly"]["order"] = {}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("FAIL MACHINE-VERIFIED artifacts[0].type", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED relations[0].sources[0]", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED assembly.order", result.stdout)

    def test_mixed_canonical_masters_in_one_clip_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            pre_two = self.write_image(root, "pre-two", (512, 512), (4, 5, 6, 255))
            master_two = self.write_image(root, "master-two", (512, 512), (4, 5, 6, 255))
            pre_two["type"] = "high-resolution-pre-master"
            master_two["type"] = "canonical-master"
            manifest["artifacts"].extend((pre_two, master_two))
            manifest["relations"].extend(
                (
                    {
                        "id": "lock-master-two",
                        "type": "canonical-lock",
                        "sources": ["pre-two"],
                        "target": "master-two",
                        "outline_enabled": False,
                        "outline_target_width": "none",
                    },
                ),
            )
            reference_k3 = next(relation for relation in manifest["relations"] if relation["id"] == "reference-k3")
            reference_k3["sources"] = ["master-two"]
            for review in manifest["reviews"]:
                if review["declared_order"] >= 2:
                    review["declared_order"] += 1
            manifest["reviews"].append(
                {
                    "id": "review-master-two",
                    "subject": "master-two",
                    "stage": "canonical-lock",
                    "status": "approved",
                    "reviewer": "reviewer-1",
                    "declared_order": 2,
                },
            )
            for transform in manifest["transforms"]:
                transform["declared_order"] += 1
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].canonical-master", result.stdout)

    def test_repeated_closing_target_from_distinct_high_resolution_source_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (root / "t3.png").write_bytes((root / "t0.png").read_bytes())
            t3 = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "t3")
            t3["sha256"] = hashlib.sha256((root / "t3.png").read_bytes()).hexdigest()
            sheet = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            for index in range(4):
                with Image.open(root / f"t{index}.png") as image:
                    sheet.alpha_composite(image, ((index % 2) * 4, (index // 2) * 4))
            sheet.save(root / "sheet.png")
            sheet_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "sheet")
            sheet_artifact["sha256"] = hashlib.sha256((root / "sheet.png").read_bytes()).hexdigest()
            manifest["clips"][0]["loop"] = True
            manifest["clips"][0]["repeated_closing_target"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_undeclared_or_misplaced_duplicate_target_pixels_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (root / "t2.png").write_bytes((root / "t0.png").read_bytes())
            t2 = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "t2")
            t2["sha256"] = hashlib.sha256((root / "t2.png").read_bytes()).hexdigest()
            sheet = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            for index in range(4):
                with Image.open(root / f"t{index}.png") as image:
                    sheet.alpha_composite(image, ((index % 2) * 4, (index // 2) * 4))
            sheet.save(root / "sheet.png")
            sheet_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "sheet")
            sheet_artifact["sha256"] = hashlib.sha256((root / "sheet.png").read_bytes()).hexdigest()
            manifest["clips"][0]["loop"] = True
            manifest["clips"][0]["repeated_closing_target"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].target-pixels", result.stdout)

    def test_huge_frame_count_fails_without_allocating_a_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["contract"]["frame_count"] = 10**100
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("FAIL MACHINE-VERIFIED clips.frames.index", result.stdout)

    def test_wrong_high_resolution_canvas_and_missing_artifact_bracket_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            Image.new("RGBA", (1, 1), (1, 2, 3, 255)).save(root / "i1.png")
            i1 = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "i1")
            i1["sha256"] = hashlib.sha256((root / "i1.png").read_bytes()).hexdigest()
            i1["width"] = 1
            i1["height"] = 1
            manifest["relations"] = [relation for relation in manifest["relations"] if relation["id"] != "bracket-i1"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED artifacts[3].high-resolution-canvas", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].frame[index=1].adjacent-keyframe-reference", result.stdout)

    def test_reused_keyframe_and_in_between_artifacts_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            frames = manifest["clips"][0]["frames"]
            frames[2]["high_resolution"] = "i1"
            frames[3]["high_resolution"] = "k0"
            for transform in manifest["transforms"]:
                if transform["target"] == "t2":
                    transform["source"] = "i1"
                if transform["target"] == "t3":
                    transform["source"] = "k0"
            for relation in manifest["relations"]:
                if relation["type"] == "adjacent-keyframe-reference":
                    relation["sources"] = ["k0", "k0"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].keyframes", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].in-betweens", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED clips.frames.high_resolution", result.stdout)

    def test_duplicate_pixels_or_orphan_artifact_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (root / "k3.png").write_bytes((root / "k0.png").read_bytes())
            k3 = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "k3")
            k3["sha256"] = hashlib.sha256((root / "k3.png").read_bytes()).hexdigest()
            orphan = self.write_image(root, "orphan", (4, 4), (3, 4, 5, 255))
            manifest["artifacts"].append(orphan)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL MACHINE-VERIFIED clips[0].keyframe-pixels", result.stdout)
        self.assertIn("FAIL MACHINE-VERIFIED artifact-graph.target-frame", result.stdout)

    def test_loop_tail_in_between_accepts_wrapped_keyframes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = self.make_fixture(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            clip = manifest["clips"][0]
            clip["loop"] = True
            frames = clip["frames"]
            frames[0], frames[1], frames[2], frames[3] = frames[0], frames[1], frames[3], frames[2]
            frames[2]["index"] = 2
            frames[2]["target"] = "t2"
            frames[1]["next_keyframe"] = 2
            frames[3]["index"] = 3
            frames[3]["target"] = "t3"
            frames[3]["previous_keyframe"] = 2
            frames[3]["next_keyframe"] = 0
            for transform in manifest["transforms"]:
                if transform["target"] == "t2":
                    transform["source"] = "k3"
                if transform["target"] == "t3":
                    transform["source"] = "i2"
            for relation in manifest["relations"]:
                if relation["id"] == "bracket-i1":
                    relation["sources"] = ["k0", "k3"]
                if relation["id"] == "bracket-i2":
                    relation["sources"] = ["k3", "k0"]
            manifest["assembly"]["targets"] = ["t0", "t1", "t2", "t3"]
            sheet = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            for index in range(4):
                with Image.open(root / f"t{index}.png") as image:
                    sheet.alpha_composite(image, ((index % 2) * 4, (index // 2) * 4))
            sheet.save(root / "sheet.png")
            sheet_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["id"] == "sheet")
            sheet_artifact["sha256"] = hashlib.sha256((root / "sheet.png").read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(manifest_path)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
