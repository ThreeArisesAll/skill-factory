#!/usr/bin/env python3
"""Validate an atomic transcript package and bind every artifact hash."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_MANIFEST_PATHS = (
    ("source", "url"),
    ("source", "platform"),
    ("source", "video_id"),
    ("source", "title"),
    ("source", "duration_seconds"),
    ("access", "probe_attempts"),
    ("access", "paywall_outcome"),
    ("access", "drm_outcome"),
    ("captions", "tracks"),
    ("transcription", "used"),
    ("lineage", "source_authority"),
    ("lineage", "source_corrected"),
    ("lineage", "chinese_from"),
    ("lineage", "english_from"),
)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_relative(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError(f"required path escapes delivery root: {value}")
    return candidate


def nested_value(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if manifest.get("decision_mode") not in {"unattended", "interactive"}:
        missing.append("decision_mode")
    if not isinstance(manifest.get("transitions"), list) or not manifest["transitions"]:
        missing.append("transitions")
    probe_attempts = nested_value(manifest, ("access", "probe_attempts"))
    if not isinstance(probe_attempts, list) or not probe_attempts:
        missing.append("access.probe_attempts")
    duration = nested_value(manifest, ("source", "duration_seconds"))
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        missing.append("source.duration_seconds")
    caption_selected = nested_value(manifest, ("captions", "selected"))
    transcription_used = nested_value(manifest, ("transcription", "used"))
    if bool(caption_selected) == bool(transcription_used):
        missing.append("source_branch")
    for path in REQUIRED_MANIFEST_PATHS:
        value = nested_value(manifest, path)
        if value is None or value == "":
            missing.append(".".join(path))
    return missing


def heading_levels(path: Path) -> list[int]:
    levels: list[int] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        marker = stripped.split(maxsplit=1)[0]
        if marker and set(marker) == {"#"} and len(marker) <= 6 and len(stripped) > len(marker):
            levels.append(len(marker))
    return levels


def append_transition(manifest: dict[str, Any], state: str, reason: str) -> None:
    transitions = manifest.setdefault("transitions", [])
    if transitions and transitions[-1].get("state") == state:
        return
    transitions.append(
        {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "reason": reason,
        }
    )


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--require", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"delivery root does not exist: {root}")
    if manifest_path.parent != root or not manifest_path.is_file():
        raise SystemExit("manifest must be an existing direct child of the delivery root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "video-transcript-package/v1":
        raise SystemExit("unsupported or missing manifest schema_version")

    missing: list[str] = validate_manifest(manifest)
    for value in args.require:
        try:
            path = resolve_relative(root, value)
        except ValueError as error:
            raise SystemExit(str(error)) from error
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            missing.append(value)

    zh_chaptered = root / "zh" / "chaptered-transcript.md"
    en_chaptered = root / "en" / "chaptered-transcript.md"
    if zh_chaptered.is_file() and en_chaptered.is_file():
        zh_levels = heading_levels(zh_chaptered)
        en_levels = heading_levels(en_chaptered)
        if not zh_levels or zh_levels != en_levels:
            missing.append("chapter_heading_structure")

    artifacts: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        if path.is_symlink() or root not in path.resolve().parents:
            missing.append(path.relative_to(root).as_posix())
            continue
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hash_file(path),
            }
        )

    manifest["artifacts"] = artifacts
    manifest["validation"] = {"required": args.require, "missing": missing}
    manifest["status"] = "complete" if not missing else "incomplete"
    append_transition(
        manifest,
        manifest["status"],
        "atomic validation passed" if not missing else "atomic validation found contract gaps",
    )
    atomic_json(manifest_path, manifest)
    print(json.dumps(manifest["validation"], ensure_ascii=False, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
