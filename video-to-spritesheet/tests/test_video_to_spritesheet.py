from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "video_to_spritesheet.py"
SPEC = importlib.util.spec_from_file_location("video_to_spritesheet", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class GeometryTests(unittest.TestCase):
    def test_non_square_geometry_preserves_aspect_ratio(self) -> None:
        self.assertEqual(MODULE._working_size(1920, 1080), (910, 512))
        self.assertEqual(MODULE._target_size(1920, 1080, 44), (78, 44))
        self.assertEqual(MODULE._target_size(1080, 1920, 44), (44, 78))

    def test_target_short_edge_contract_rejects_non_multiple_of_four(self) -> None:
        with self.assertRaisesRegex(MODULE.PipelineError, "divisible by four"):
            MODULE._target_size(512, 512, 231)


class MatteTests(unittest.TestCase):
    def test_edge_connectivity_does_not_delete_enclosed_similar_foreground(self) -> None:
        rgb = np.full((96, 96, 3), (180, 60, 100), dtype=np.uint8)
        cv2.rectangle(rgb, (18, 18), (77, 77), (25, 35, 55), thickness=-1)
        cv2.rectangle(rgb, (34, 34), (46, 51), (186, 65, 105), thickness=-1)
        color, _, residual = MODULE.estimate_background(rgb, border_width=8, tolerance=22.0)
        rgba, _ = MODULE.cutout_frame(
            rgb,
            background_colors=(color,),
            tolerance=22.0,
            feather_width=1.5,
            decontaminate=1.0,
            residual_p95=residual,
        )
        self.assertGreater(int(rgba[42, 40, 3]), 240)
        self.assertEqual(int(rgba[0, 0, 3]), 0)

    def test_enclosed_background_pocket_is_cleared(self) -> None:
        rgb = np.full((96, 96, 3), (235, 235, 230), dtype=np.uint8)
        cv2.rectangle(rgb, (15, 15), (80, 80), (30, 50, 90), thickness=-1)
        cv2.circle(rgb, (48, 48), 8, (235, 235, 230), thickness=-1)
        color, _, residual = MODULE.estimate_background(rgb, border_width=8, tolerance=22.0)
        rgba, _ = MODULE.cutout_frame(
            rgb,
            background_colors=(color,),
            tolerance=22.0,
            feather_width=1.5,
            decontaminate=1.0,
            residual_p95=residual,
        )
        self.assertLess(int(rgba[48, 48, 3]), 8)
        self.assertGreater(int(rgba[48, 30, 3]), 248)

    def test_decontamination_preserves_opaque_rgb_and_zeros_transparent_rgb(self) -> None:
        rgb = np.full((64, 64, 3), (20, 200, 40), dtype=np.uint8)
        rgb[16:48, 16:48] = (70, 80, 210)
        color, _, residual = MODULE.estimate_background(rgb, border_width=6, tolerance=22.0)
        rgba, _ = MODULE.cutout_frame(
            rgb,
            background_colors=(color,),
            tolerance=22.0,
            feather_width=1.0,
            decontaminate=1.0,
            residual_p95=residual,
        )
        self.assertTupleEqual(tuple(rgba[32, 32, :3]), (70, 80, 210))
        self.assertTrue(np.all(rgba[rgba[:, :, 3] == 0, :3] == 0))

    def test_outline_is_outward_and_does_not_fill_internal_hole(self) -> None:
        rgba = np.zeros((96, 96, 4), dtype=np.uint8)
        cv2.circle(rgba, (48, 48), 24, (80, 90, 110, 255), thickness=-1)
        cv2.circle(rgba, (48, 48), 8, (0, 0, 0, 0), thickness=-1)
        output = MODULE.add_outline(rgba, width=6.0, color=(24, 20, 28))
        self.assertEqual(int(output[48, 48, 3]), 0)
        self.assertGreater(int(output[48, 19, 3]), 0)
        self.assertTupleEqual(tuple(output[48, 48, :3]), (0, 0, 0))

    def test_premultiplied_lanczos_does_not_reveal_hidden_rgb(self) -> None:
        rgba = np.zeros((64, 64, 4), dtype=np.uint8)
        rgba[:, :, :3] = (255, 0, 255)
        rgba[16:48, 16:48] = (20, 80, 210, 255)
        resized = MODULE.resize_premultiplied(rgba, (16, 16))
        self.assertTrue(np.all(resized[resized[:, :, 3] == 0, :3] == 0))
        partial = (resized[:, :, 3] > 0) & (resized[:, :, 3] < 255)
        self.assertTrue(np.all(resized[partial, 0] <= 20))

    def test_remote_tiny_capture_artifact_is_removed(self) -> None:
        rgba = np.zeros((128, 128, 4), dtype=np.uint8)
        cv2.circle(rgba, (50, 64), 28, (80, 100, 160, 255), thickness=-1)
        cv2.rectangle(rgba, (118, 118), (119, 119), (240, 240, 240, 255), thickness=-1)
        cleaned, diagnostics = MODULE.suppress_detached_artifacts(rgba)
        self.assertEqual(diagnostics["removed_component_count"], 1)
        self.assertEqual(int(cleaned[118, 118, 3]), 0)
        self.assertEqual(int(cleaned[64, 50, 3]), 255)

    def test_remote_material_foreground_causes_typed_failure(self) -> None:
        rgba = np.zeros((128, 128, 4), dtype=np.uint8)
        cv2.circle(rgba, (42, 64), 28, (80, 100, 160, 255), thickness=-1)
        cv2.rectangle(rgba, (105, 48), (120, 78), (240, 240, 240, 255), thickness=-1)
        with self.assertRaisesRegex(MODULE.PipelineError, "cannot be attributed safely"):
            MODULE.suppress_detached_artifacts(rgba)

    def test_resize_island_cleanup_keeps_near_edge_antialiasing(self) -> None:
        rgba = np.zeros((64, 64, 4), dtype=np.uint8)
        cv2.rectangle(rgba, (20, 16), (44, 50), (30, 40, 60, 255), thickness=-1)
        rgba[15, 30] = (30, 40, 60, 2)
        rgba[2, 60] = (255, 0, 255, 1)
        cleaned, diagnostics = MODULE.suppress_resize_islands(rgba)
        self.assertEqual(int(cleaned[15, 30, 3]), 2)
        self.assertEqual(int(cleaned[2, 60, 3]), 0)
        self.assertEqual(diagnostics["removed_resize_island_count"], 1)


class QualityTests(unittest.TestCase):
    def test_fixed_seed_synthetic_truth_passes_frozen_gates(self) -> None:
        report = MODULE.synthetic_quality(
            tolerance=22.0,
            border_width=12,
            feather_width=1.5,
            decontaminate=1.0,
        )
        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["seed"], 20260815)

    def test_obviously_degraded_matte_fails_mandatory_gates(self) -> None:
        _, _, truth = MODULE._synthetic_cases()[0]
        degraded = np.zeros(truth.shape[:2], dtype=np.uint8)
        metrics = MODULE._mask_metrics(degraded, truth[:, :, 3])
        failures = [
            metrics["iou"] < MODULE.SYNTHETIC_THRESHOLDS["minimum_iou"],
            metrics["recall"] < MODULE.SYNTHETIC_THRESHOLDS["minimum_recall"],
            metrics["alpha_mae"] > MODULE.SYNTHETIC_THRESHOLDS["maximum_alpha_mae"],
        ]
        self.assertTrue(all(failures), metrics)

    def test_temporal_gate_marks_large_outlier_and_loop_seam(self) -> None:
        base = np.zeros((64, 64), dtype=np.uint8)
        cv2.circle(base, (32, 32), 12, 255, thickness=-1)
        frames = [np.roll(base, index, axis=1) for index in (0, 1, 2, 3, 18)]
        report = MODULE.animation_quality(frames)
        failing_pairs = {(item["from_frame"], item["to_frame"]) for item in report["failures"]}
        self.assertIn((3, 4), failing_pairs)
        self.assertIn((4, 0), failing_pairs)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class EndToEndTests(unittest.TestCase):
    def _make_video(self, root: Path) -> Path:
        source = root / "source"
        source.mkdir()
        for index in range(12):
            image = Image.new("RGB", (128, 96), (122, 24, 61))
            draw = ImageDraw.Draw(image)
            x = 64 + int(round(4 * np.sin(2 * np.pi * index / 11)))
            draw.ellipse((x - 25, 20, x + 25, 78), fill=(27, 23, 31), outline=(18, 14, 22), width=4)
            draw.ellipse((x - 19, 26, x + 19, 72), fill=(230, 184, 95))
            image.save(source / f"frame-{index:04d}.png")
        video = root / "input.mkv"
        completed = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", "12", "-i", str(source / "frame-%04d.png"),
                "-c:v", "ffv1", str(video),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return video

    def test_cli_run_verify_and_tamper_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = self._make_video(root)
            output = root / "output"
            result = MODULE.main(
                [
                    "run", "--input", str(video), "--output", str(output),
                    "--target-short-edge", "64", "--cycle-start", "0",
                    "--cycle-end", str(11 / 12),
                ]
            )
            self.assertEqual(result, 0)
            job = json.loads((output / "job.json").read_text(encoding="utf-8"))
            self.assertEqual(len(job["frame_timing"]), 12)
            self.assertEqual(job["spritesheet"]["columns"], 4)
            with Image.open(output / "spritesheet.png") as sheet:
                self.assertEqual(sheet.mode, "RGBA")
            frame = output / "frames" / "final" / "frame-0000.png"
            frame.write_bytes(frame.read_bytes() + b"tamper")
            with self.assertRaisesRegex(MODULE.PipelineError, "verification failed"):
                MODULE.verify_output(output, emit=False)

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = self._make_video(root)
            output = root / "unused"
            result = MODULE.main(
                [
                    "run", "--input", str(video), "--output", str(output),
                    "--target-short-edge", "44", "--dry-run",
                ]
            )
            self.assertEqual(result, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
