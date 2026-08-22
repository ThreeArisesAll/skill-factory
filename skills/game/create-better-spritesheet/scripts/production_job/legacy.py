"""Narrow subprocess adapters for the internal canonical v3 and package v4/v5 pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .contracts import ProductionError

PIPELINE = Path(__file__).parents[1] / "spritesheet_pipeline.py"


def run_legacy(*arguments: str) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(PIPELINE), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode:
        diagnostic = "\n".join(part for part in (completed.stdout, completed.stderr) if part).lower()
        if arguments and arguments[0] == "prepare-canonical" and (
            "unbacked low-alpha boundary" in diagnostic
            or "canonical alpha gate" in diagnostic
            or "enabled outline requires an opaque silhouette seed" in diagnostic
        ):
            raise ProductionError(
                "CANONICAL_ALPHA_GATE_FAILED",
                "canonical preparation failed the pre-admission Alpha gate",
                {"adapter": "canonical-admission-v3"},
            )
        raise ProductionError(
            "LEGACY_ADAPTER_FAILED",
            "the internal spritesheet pipeline rejected the projected request",
            {"adapter": "legacy-v4"},
        )
