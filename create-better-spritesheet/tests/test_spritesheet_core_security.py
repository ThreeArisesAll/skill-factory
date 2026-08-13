from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).parents[1] / "scripts"
SCRIPT = SCRIPTS / "spritesheet_pipeline.py"
sys.path.insert(0, str(SCRIPTS))

from spritesheet_core.errors import ContractError
from spritesheet_core.package_io import (
    ResourceBudget,
    atomic_directory,
    read_regular_file_snapshot,
    sha256_file,
)
from spritesheet_core.rendering import open_rgba_snapshot


class SpritesheetCoreSecurityTests(unittest.TestCase):
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

    def test_atomic_directory_never_replaces_broken_symlink_or_raced_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            broken_output = root / "broken-output"
            broken_output.symlink_to(root / "missing-target", target_is_directory=True)
            build_called = False

            def unexpected_build(_: Path) -> None:
                nonlocal build_called
                build_called = True

            with self.assertRaisesRegex(ContractError, "output directory already exists"):
                atomic_directory(broken_output, unexpected_build)
            self.assertFalse(build_called)
            self.assertTrue(broken_output.is_symlink())

            raced_output = root / "raced-output"

            def race_build(destination: Path) -> None:
                (destination / "payload.txt").write_text("candidate", encoding="utf-8")
                raced_output.mkdir()

            with self.assertRaisesRegex(ContractError, "output directory already exists"):
                atomic_directory(raced_output, race_build)
            self.assertTrue(raced_output.is_dir())
            self.assertEqual(list(raced_output.iterdir()), [])

    def test_regular_file_snapshot_rejects_symlinks_and_bounds_read_before_allocation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.bin"
            source.write_bytes(b"stable bytes")
            snapshot = read_regular_file_snapshot(source, "fixture", 32)
            self.assertEqual(snapshot.data, b"stable bytes")
            self.assertEqual(snapshot.sha256, sha256_file(source, max_bytes=32))

            linked = root / "linked.bin"
            linked.symlink_to(source)
            with self.assertRaisesRegex(ContractError, "regular non-symlink file"):
                read_regular_file_snapshot(linked, "fixture", 32)
            with self.assertRaisesRegex(ContractError, "regular non-symlink file"):
                sha256_file(linked, max_bytes=32)

            oversized = root / "oversized.bin"
            oversized.write_bytes(b"123456789")
            with self.assertRaisesRegex(ContractError, "fixture file exceeds 8 bytes"):
                read_regular_file_snapshot(oversized, "fixture", 8)

    def test_cli_rejects_oversized_json_and_frame_count_before_deep_processing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            oversized = root / "oversized.json"
            oversized.write_text(
                json.dumps(
                    {
                        "schema_version": "canonical-authoring-request/v3",
                        "padding": "x" * (8 * 1024 * 1024),
                    },
                ),
                encoding="utf-8",
            )
            oversized_result = self.run_cli(
                "prepare-canonical",
                "--request",
                str(oversized),
                "--output-dir",
                str(root / "unused"),
            )
            self.assertEqual(oversized_result.returncode, 1)
            self.assertIn("request file exceeds 8388608 bytes", oversized_result.stdout)

            request = root / "excessive-frame-count.json"
            request.write_text(
                json.dumps(
                    {
                        "schema_version": "spritesheet-production-request/v4",
                        "contract": {
                            "frame_width": 32,
                            "frame_height": 32,
                            "frame_count": 4097,
                            "high_resolution_short_side": 512,
                            "sampler": "lanczos-premultiplied-v1",
                            "outline": {"enabled": False, "target_width": "none"},
                            "animation_origin": [0, 0],
                            "anchor": [16, 31],
                            "safe_bounds": [2, 2, 30, 30],
                        },
                        "canonical_references": [],
                        "clips": [],
                        "reviews": [],
                        "grid": {"columns": 1, "order": "row-major"},
                    },
                ),
                encoding="utf-8",
            )
            count_result = self.run_cli(
                "build-package",
                "--request",
                str(request),
                "--output-dir",
                str(root / "package"),
            )
            self.assertEqual(count_result.returncode, 1)
            self.assertIn("contract.frame_count must not exceed 4096", count_result.stdout)

    def test_legacy_pipeline_module_reexports_established_names(self) -> None:
        spec = importlib.util.spec_from_file_location("legacy_pipeline", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        expected_names = {
            "CANONICAL_REQUEST_SCHEMA",
            "PRODUCTION_REQUEST_SCHEMA",
            "PACKAGE_SCHEMA",
            "ContractError",
            "sha256_file",
            "prepare_canonical",
            "build_package",
            "verify_package",
            "canonical_admission_proof",
            "parse_production_request",
        }
        self.assertEqual(expected_names - set(vars(module)), set())

    def test_legacy_parse_production_request_returns_mutable_plain_dict(self) -> None:
        pipeline_test_path = Path(__file__).with_name("test_spritesheet_pipeline.py")
        pipeline_spec = importlib.util.spec_from_file_location(
            "security_pipeline_tests",
            pipeline_test_path,
        )
        pipeline_tests = importlib.util.module_from_spec(pipeline_spec)
        assert pipeline_spec.loader is not None
        pipeline_spec.loader.exec_module(pipeline_tests)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = pipeline_tests.SpritesheetPipelineTests(methodName="runTest")
            request, _ = fixture.make_production_request(root)
            spec = importlib.util.spec_from_file_location("legacy_pipeline", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            parsed = module.parse_production_request(request)
            self.assertIs(type(parsed), dict)
            self.assertNotIn("artifact_bytes", parsed)
            copied = parsed.copy()
            parsed["compatibility_probe"] = True
            self.assertNotIn("compatibility_probe", copied)
            self.assertEqual(copied, dict(copied))

    def test_resource_budget_rejects_aggregate_bytes_and_pixels_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = root / "first.png"
            second = root / "second.png"
            Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(first)
            Image.new("RGBA", (4, 4), (0, 255, 0, 255)).save(second)

            byte_budget = ResourceBudget(max_bytes=first.stat().st_size + second.stat().st_size - 1)
            open_rgba_snapshot(first, "first", budget=byte_budget)
            with self.assertRaisesRegex(ContractError, "aggregate file bytes exceed"):
                open_rgba_snapshot(second, "second", budget=byte_budget)

            pixel_budget = ResourceBudget(max_bytes=1024, max_decoded_pixels=31)
            open_rgba_snapshot(first, "first", budget=pixel_budget)
            with self.assertRaisesRegex(ContractError, "aggregate decoded pixels exceed"):
                open_rgba_snapshot(second, "second", budget=pixel_budget)


if __name__ == "__main__":
    unittest.main()
