#!/usr/bin/env python3
"""Create or reuse the isolated downloader and Whisper tool environment."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def executable(venv: Path, name: str) -> Path:
    directory = "Scripts" if os.name == "nt" else "bin"
    return venv / directory / name


def ensure_venv(cache_root: Path) -> Path:
    venv = cache_root / "venv"
    python = executable(venv, "python")
    if not python.exists():
        cache_root.mkdir(parents=True, exist_ok=True)
        run([sys.executable, "-m", "venv", str(venv)])
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    return venv


def ensure_component(venv: Path, component: str) -> None:
    python = executable(venv, "python")
    if component == "downloader":
        binary = executable(venv, "yt-dlp")
        package = "yt-dlp"
    else:
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise SystemExit("mlx-whisper requires an Apple silicon Mac")
        binary = executable(venv, "mlx_whisper")
        package = "mlx-whisper"
    if not binary.exists():
        run([str(python), "-m", "pip", "install", "--upgrade", package])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=("downloader", "whisper"), required=True)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.home() / ".codex" / "cache" / "download-video-transcripts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_root = args.cache_root.expanduser().resolve()
    venv = ensure_venv(cache_root)
    ensure_component(venv, args.component)
    yt_dlp = executable(venv, "yt-dlp")
    mlx_whisper = executable(venv, "mlx_whisper")
    result = {
        "cache_root": str(cache_root),
        "python": str(executable(venv, "python")),
        "yt_dlp": str(yt_dlp) if yt_dlp.exists() else None,
        "mlx_whisper": str(mlx_whisper) if mlx_whisper.exists() else None,
        "huggingface_home": str(cache_root / "huggingface"),
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
