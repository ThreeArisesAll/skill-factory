#!/usr/bin/env python3
"""Normalize and deterministically rank caption tracks from yt-dlp metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TIMESTAMP = re.compile(
    r"(?P<sh>\d{1,2}):(?P<sm>\d{2}):(?P<ss>\d{2})[,.](?P<sms>\d{3})\s+-->\s+"
    r"(?P<eh>\d{1,2}):(?P<em>\d{2}):(?P<es>\d{2})[,.](?P<ems>\d{3})"
)


def normalize_language(value: str | None) -> str:
    return (value or "").strip().replace("_", "-").lower()


def language_matches(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left == right or left.split("-", 1)[0] == right.split("-", 1)[0]


def format_marks_original(formats: list[Any]) -> bool:
    for item in formats:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).casefold()
        if "original" in name or bool(item.get("is_original")):
            return True
    return False


def seconds(hours: str, minutes: str, whole: str, millis: str) -> float:
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def coverage(path: Path) -> dict[str, float | int]:
    intervals: list[tuple[float, float]] = []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for match in TIMESTAMP.finditer(text):
        start = seconds(match["sh"], match["sm"], match["ss"], match["sms"])
        end = seconds(match["eh"], match["em"], match["es"], match["ems"])
        if end > start:
            intervals.append((start, end))
    intervals.sort()
    merged: list[list[float]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return {
        "cue_count": len(intervals),
        "covered_seconds": round(sum(end - start for start, end in merged), 3),
    }


def candidate_files(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"invalid --candidate-file value: {value}")
        key, raw_path = value.split("=", 1)
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"candidate file does not exist: {path}")
        result[key] = path
    return result


def track_records(info: dict[str, Any], files: dict[str, Path]) -> list[dict[str, Any]]:
    original = normalize_language(info.get("language") or info.get("original_language"))
    default_language = normalize_language(info.get("default_subtitle_language"))
    records: list[dict[str, Any]] = []
    for kind, field in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        mapping = info.get(field) or {}
        for language, formats in mapping.items():
            normalized = normalize_language(language)
            is_original = (
                language_matches(normalized, original)
                or normalized.endswith("-orig")
                or format_marks_original(formats)
            )
            rank = 1 if kind == "manual" and is_original else 2 if is_original else 3 if kind == "manual" else 4
            key = f"{kind}:{language}"
            measured = coverage(files[key]) if key in files else None
            records.append(
                {
                    "key": key,
                    "language": language,
                    "normalized_language": normalized,
                    "kind": kind,
                    "is_original": is_original,
                    "is_platform_default": bool(
                        language_matches(normalized, default_language)
                        or any(bool(item.get("default")) for item in formats if isinstance(item, dict))
                    ),
                    "rank": rank,
                    "formats": sorted(
                        {str(item.get("ext", "unknown")) for item in formats if isinstance(item, dict)}
                    ),
                    "coverage": measured,
                }
            )
    return records


def sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    measured = record.get("coverage") or {}
    return (
        record["rank"],
        -float(measured.get("covered_seconds", -1)),
        -int(measured.get("cue_count", -1)),
        not record["is_platform_default"],
        record["normalized_language"],
        record["kind"],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--info", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-file", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    info = json.loads(args.info.read_text(encoding="utf-8"))
    if info.get("_type") in {"playlist", "multi_video"} or info.get("entries"):
        raise SystemExit("metadata expands to multiple entries; address one video explicitly")
    records = sorted(track_records(info, candidate_files(args.candidate_file)), key=sort_key)
    chosen = records[0] if records else None
    if chosen is None:
        reason = "no downloadable caption tracks"
    else:
        reason = (
            f"rank {chosen['rank']}; coverage {chosen['coverage']}; "
            f"platform_default={chosen['is_platform_default']}"
        )
    result = {
        "schema_version": "subtitle-inventory/v1",
        "video_id": info.get("id"),
        "title": info.get("title"),
        "duration_seconds": info.get("duration"),
        "original_language": info.get("language") or info.get("original_language"),
        "tracks": records,
        "chosen": chosen,
        "selection_reason": reason,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
