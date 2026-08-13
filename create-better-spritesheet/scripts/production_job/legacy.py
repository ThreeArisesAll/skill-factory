"""Narrow subprocess adapters for the internal v3/v4 pipeline."""

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
        raise ProductionError(
            "LEGACY_ADAPTER_FAILED",
            "the internal spritesheet pipeline rejected the projected request",
            {"adapter": "legacy-v4"},
        )
