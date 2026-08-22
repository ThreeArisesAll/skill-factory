#!/usr/bin/env python3
"""Self-contained regression tests for transcript package helpers."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent


class ContractToolsTest(unittest.TestCase):
    @staticmethod
    def manifest() -> dict[str, object]:
        return {
            "schema_version": "video-transcript-package/v1",
            "status": "chaptered",
            "decision_mode": "unattended",
            "source": {
                "url": "https://example.invalid/video",
                "platform": "youtube",
                "video_id": "one",
                "title": "Example",
                "duration_seconds": 60,
            },
            "access": {
                "probe_attempts": [{"profile": "anonymous", "outcome": "success"}],
                "paywall_outcome": "not_detected",
                "drm_outcome": "not_detected",
            },
            "captions": {"tracks": [], "selected": None},
            "transcription": {"used": True},
            "lineage": {
                "source_authority": "source/whisper.json",
                "source_corrected": "zh/corrected-transcript.txt",
                "chinese_from": "zh/corrected-transcript.txt",
                "english_from": "zh/corrected-transcript.txt",
            },
            "transitions": [{"state": "chaptered", "at": "2026-08-15T00:00:00Z"}],
        }

    def test_inventory_prefers_original_manual(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            info = root / "info.json"
            output = root / "inventory.json"
            info.write_text(
                json.dumps(
                    {
                        "id": "one",
                        "title": "Example",
                        "duration": 60,
                        "language": "zh-Hans",
                        "subtitles": {"en": [{"ext": "vtt"}], "zh": [{"ext": "srt"}]},
                        "automatic_captions": {"zh": [{"ext": "json3"}]},
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, str(SCRIPTS / "subtitle_inventory.py"), "--info", str(info), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["chosen"]["key"], "manual:zh")

    def test_inventory_recognizes_original_track_name(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            info = root / "info.json"
            output = root / "inventory.json"
            info.write_text(
                json.dumps(
                    {
                        "id": "named-original",
                        "title": "Example",
                        "duration": 60,
                        "automatic_captions": {
                            "de": [{"ext": "vtt", "name": "German"}],
                            "en": [{"ext": "vtt", "name": "English (Original)"}],
                        },
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, str(SCRIPTS / "subtitle_inventory.py"), "--info", str(info), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["chosen"]["key"], "automatic:en")
            self.assertEqual(result["chosen"]["rank"], 2)

    def test_inventory_uses_coverage_for_same_tier(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            info = root / "info.json"
            short = root / "short.srt"
            long = root / "long.srt"
            output = root / "inventory.json"
            info.write_text(
                json.dumps(
                    {
                        "id": "two",
                        "title": "Example",
                        "duration": 60,
                        "subtitles": {"en": [{"ext": "srt"}], "fr": [{"ext": "srt"}]},
                    }
                ),
                encoding="utf-8",
            )
            short.write_text("1\n00:00:00,000 --> 00:00:05,000\nA\n", encoding="utf-8")
            long.write_text("1\n00:00:00,000 --> 00:00:20,000\nB\n", encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "subtitle_inventory.py"),
                    "--info",
                    str(info),
                    "--output",
                    str(output),
                    "--candidate-file",
                    f"manual:en={short}",
                    "--candidate-file",
                    f"manual:fr={long}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["chosen"]["key"], "manual:fr")

    def test_finalize_marks_missing_package_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / "processing-manifest.json"
            manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "finalize_delivery.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                    "--require",
                    "zh/corrected-transcript.txt",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(updated["status"], "incomplete")

    def test_finalize_hashes_complete_package(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "zh").mkdir()
            artifact = root / "zh" / "corrected-transcript.txt"
            artifact.write_text("content\n", encoding="utf-8")
            manifest = root / "processing-manifest.json"
            manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "finalize_delivery.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                    "--require",
                    "zh/corrected-transcript.txt",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(updated["status"], "complete")
            self.assertEqual(updated["artifacts"][0]["path"], "zh/corrected-transcript.txt")
            self.assertEqual(len(updated["artifacts"][0]["sha256"]), 64)
            self.assertEqual(updated["transitions"][-1]["state"], "complete")

    def test_finalize_rejects_incomplete_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "zh").mkdir()
            artifact = root / "zh" / "corrected-transcript.txt"
            artifact.write_text("content\n", encoding="utf-8")
            value = self.manifest()
            value["lineage"] = {}
            manifest = root / "processing-manifest.json"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "finalize_delivery.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                    "--require",
                    "zh/corrected-transcript.txt",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("lineage.source_authority", updated["validation"]["missing"])

    def test_finalize_requires_exactly_one_source_branch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "zh").mkdir()
            artifact = root / "zh" / "corrected-transcript.txt"
            artifact.write_text("content\n", encoding="utf-8")
            value = self.manifest()
            value["transcription"] = {"used": False}
            manifest = root / "processing-manifest.json"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "finalize_delivery.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                    "--require",
                    "zh/corrected-transcript.txt",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("source_branch", updated["validation"]["missing"])

    def test_finalize_rejects_mismatched_heading_structure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "zh").mkdir()
            (root / "en").mkdir()
            zh = root / "zh" / "chaptered-transcript.md"
            en = root / "en" / "chaptered-transcript.md"
            zh.write_text("# Title\n\n## Section\n", encoding="utf-8")
            en.write_text("# Title\n\n### Section\n", encoding="utf-8")
            manifest = root / "processing-manifest.json"
            manifest.write_text(json.dumps(self.manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "finalize_delivery.py"),
                    "--root",
                    str(root),
                    "--manifest",
                    str(manifest),
                    "--require",
                    "zh/chaptered-transcript.md",
                    "--require",
                    "en/chaptered-transcript.md",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertIn("chapter_heading_structure", updated["validation"]["missing"])


if __name__ == "__main__":
    unittest.main()
