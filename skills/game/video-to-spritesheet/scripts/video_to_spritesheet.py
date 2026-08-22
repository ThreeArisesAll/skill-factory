#!/usr/bin/env python3
"""Deterministically extract one loopable transparent spritesheet from a local video."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError as error:  # pragma: no cover - exercised without the test environment
    print(
        json.dumps(
            {
                "error": {
                    "code": "DEPENDENCY_MISSING",
                    "message": str(error),
                }
            }
        ),
        file=sys.stderr,
    )
    raise SystemExit(2) from error


SCHEMA_VERSION = "video-to-spritesheet-job/v1"
QUALITY_VERSION = "video-to-spritesheet-quality/v1"
SUPPORTED_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
CADENCE_COLLAPSE_SCHEMA = "adjacent-near-duplicate-collapse/v1"
CADENCE_COLLAPSE_THRESHOLDS = {
    "maximum_mean_alpha_difference": 0.003,
    "maximum_contour_change_ratio": 0.012,
    "maximum_area_change_ratio": 0.003,
}


class PipelineError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def payload(self) -> dict[str, object]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


@dataclass(frozen=True)
class VideoInfo:
    path: str
    sha256: str
    stream_index: int
    codec: str
    width: int
    height: int
    display_width: int
    display_height: int
    rotation: int
    average_fps: float
    duration_seconds: float
    frame_count: int | None
    variable_frame_rate: bool


@dataclass(frozen=True)
class CycleCandidate:
    start_frame: int
    end_frame: int
    frame_count: int
    pose_distance: float
    velocity_distance: float
    motion_energy: float
    score: float


@dataclass(frozen=True)
class FrameMetrics:
    boundary_residual_rate: float
    outer_edge_background_like_pixel_count: int
    outer_edge_background_like_ratio: float
    transparent_rgb_nonzero_count: int
    foreground_area: float
    foreground_area_ratio: float
    foreground_bbox: tuple[int, int, int, int] | None
    partial_alpha_pixel_count: int
    retained_background_seed_count: int
    internal_hole_count: int
    clipped_outline: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise PipelineError("DEPENDENCY_MISSING", f"required executable is unavailable: {name}")
    return executable


def _run_json(command: Sequence[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise PipelineError(
            "UNSUPPORTED_INPUT",
            "media inspection failed",
            {"command": list(command), "stderr": completed.stderr.strip()},
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise PipelineError("UNSUPPORTED_INPUT", "media inspection returned invalid JSON") from error


def _rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    numerator, denominator = value.split("/", 1)
    return float(numerator) / float(denominator)


def inspect_video(path: Path, *, requested_stream: int | None = None) -> VideoInfo:
    if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise PipelineError(
            "UNSUPPORTED_INPUT",
            "input must be one local MP4, MOV, WebM, or MKV file",
            {"input": str(path)},
        )
    ffprobe = _require_executable("ffprobe")
    payload = _run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    video_streams = [stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"]
    if not video_streams:
        raise PipelineError("UNSUPPORTED_INPUT", "input contains no decodable video stream")
    if requested_stream is None:
        if len(video_streams) > 1:
            raise PipelineError(
                "AMBIGUOUS_VIDEO_STREAM",
                "input contains multiple video streams; select one with --video-stream",
                {"stream_indices": [int(stream["index"]) for stream in video_streams]},
            )
        stream = video_streams[0]
    else:
        matches = [stream for stream in video_streams if int(stream["index"]) == requested_stream]
        if not matches:
            raise PipelineError(
                "UNSUPPORTED_INPUT",
                "requested video stream does not exist",
                {"video_stream": requested_stream},
            )
        stream = matches[0]
    tags = stream.get("tags", {})
    rotation = int(tags.get("rotate", 0) or 0) % 360
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            rotation = int(round(float(side_data["rotation"]))) % 360
    width = int(stream["width"])
    height = int(stream["height"])
    display_width, display_height = (height, width) if rotation in {90, 270} else (width, height)
    average_fps = _rate(stream.get("avg_frame_rate"))
    nominal_fps = _rate(stream.get("r_frame_rate"))
    duration = float(stream.get("duration") or payload.get("format", {}).get("duration") or 0.0)
    frame_count = int(stream["nb_frames"]) if str(stream.get("nb_frames", "")).isdigit() else None
    return VideoInfo(
        path=str(path.resolve()),
        sha256=_sha256(path),
        stream_index=int(stream["index"]),
        codec=str(stream.get("codec_name", "unknown")),
        width=width,
        height=height,
        display_width=display_width,
        display_height=display_height,
        rotation=rotation,
        average_fps=average_fps,
        duration_seconds=duration,
        frame_count=frame_count,
        variable_frame_rate=bool(average_fps and nominal_fps and abs(average_fps - nominal_fps) > 0.01),
    )


def _frame_timestamps(path: Path, stream_index: int) -> list[dict[str, float]]:
    ffprobe = _require_executable("ffprobe")
    payload = _run_json(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            str(stream_index),
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time,pkt_duration_time",
            "-of",
            "json",
            str(path),
        ]
    )
    records: list[dict[str, float]] = []
    for index, frame in enumerate(payload.get("frames", [])):
        timestamp = float(frame.get("best_effort_timestamp_time", index))
        duration = float(frame.get("pkt_duration_time", 0.0) or 0.0)
        records.append({"timestamp": timestamp, "duration": duration})
    return records


def decode_video(path: Path, info: VideoInfo, directory: Path) -> tuple[list[Path], list[dict[str, float]]]:
    ffmpeg = _require_executable("ffmpeg")
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(path),
        "-map",
        f"0:{info.stream_index}",
        "-fps_mode",
        "passthrough",
        str(directory / "decoded-%06d.png"),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise PipelineError(
            "UNSUPPORTED_INPUT",
            "video decoding failed",
            {"stderr": completed.stderr.strip()},
        )
    frames = sorted(directory.glob("decoded-*.png"))
    if len(frames) < 3:
        raise PipelineError("NO_COMPLETE_CYCLE", "video contains fewer than three decoded frames")
    timestamps = _frame_timestamps(path, info.stream_index)
    fallback_duration = 1.0 / info.average_fps if info.average_fps > 0 else 1.0 / 24.0
    if len(timestamps) != len(frames):
        timestamps = [
            {"timestamp": index * fallback_duration, "duration": fallback_duration}
            for index in range(len(frames))
        ]
    else:
        for index, record in enumerate(timestamps):
            if record["duration"] <= 0:
                if index + 1 < len(timestamps):
                    record["duration"] = max(
                        timestamps[index + 1]["timestamp"] - record["timestamp"],
                        fallback_duration,
                    )
                else:
                    record["duration"] = fallback_duration
    return frames, timestamps


def _feature(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
    gray = cv2.cvtColor(rgb / 255.0, cv2.COLOR_RGB2GRAY)
    edges = cv2.Laplacian(gray, cv2.CV_32F)
    return np.concatenate((gray.reshape(-1), edges.reshape(-1) * 0.35))


def find_cycle_candidates(frame_paths: Sequence[Path]) -> tuple[CycleCandidate, ...]:
    features = np.stack([_feature(path) for path in frame_paths])
    step_motion = np.mean(np.abs(np.diff(features, axis=0)), axis=1)
    typical_motion = max(float(np.median(step_motion)), 1e-6)
    candidates: list[CycleCandidate] = []
    minimum_frames = max(3, min(8, len(frame_paths) // 4))
    for start in range(len(frame_paths) - minimum_frames + 1):
        for end in range(start + minimum_frames - 1, len(frame_paths)):
            count = end - start + 1
            pose = float(np.mean(np.abs(features[start] - features[end])))
            start_speed = float(step_motion[start]) if start < len(step_motion) else 0.0
            end_speed = float(step_motion[end - 1]) if end > 0 else 0.0
            velocity = abs(start_speed - end_speed)
            energy = float(step_motion[start:end].mean()) if end > start else 0.0
            static_penalty = max(0.0, typical_motion * 0.25 - energy) * 4.0
            edge_penalty = 0.0 if start == 0 or end == len(frame_paths) - 1 else typical_motion * 0.02
            score = pose + velocity * 0.5 + static_penalty + edge_penalty
            candidates.append(
                CycleCandidate(
                    start_frame=start,
                    end_frame=end,
                    frame_count=count,
                    pose_distance=pose,
                    velocity_distance=velocity,
                    motion_energy=energy,
                    score=score,
                )
            )
    return tuple(sorted(candidates, key=lambda item: (item.score, -item.frame_count, item.start_frame)))


def select_cycle(
    candidates: Sequence[CycleCandidate],
    *,
    frame_count: int,
    explicit_start: int | None = None,
    explicit_end: int | None = None,
) -> CycleCandidate:
    if explicit_start is not None or explicit_end is not None:
        if explicit_start is None or explicit_end is None:
            raise PipelineError("NO_COMPLETE_CYCLE", "cycle start and end must be supplied together")
        matches = [
            candidate
            for candidate in candidates
            if candidate.start_frame == explicit_start and candidate.end_frame == explicit_end
        ]
        if not matches:
            raise PipelineError("NO_COMPLETE_CYCLE", "explicit cycle frame interval is invalid")
        selected = matches[0]
    else:
        if not candidates:
            raise PipelineError("NO_COMPLETE_CYCLE", "no cycle candidate was found")
        selected = candidates[0]
        full = next(
            (
                candidate
                for candidate in candidates
                if candidate.start_frame == 0 and candidate.end_frame == frame_count - 1
            ),
            None,
        )
        if full is not None and full.score <= selected.score * 1.15 + 1e-6:
            selected = full
        distinct = [
            candidate
            for candidate in candidates
            if abs(candidate.start_frame - selected.start_frame) > 2
            or abs(candidate.end_frame - selected.end_frame) > 2
        ]
        if distinct and distinct[0].score <= selected.score * 1.01 and selected.score > 1e-6:
            raise PipelineError(
                "AMBIGUOUS_CYCLE",
                "multiple materially different cycle candidates have indistinguishable scores",
                {"selected": asdict(selected), "alternative": asdict(distinct[0])},
            )
    if selected.motion_energy <= 1e-6:
        raise PipelineError("NO_COMPLETE_CYCLE", "selected interval contains no measurable motion")
    return selected


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    normalized = np.asarray(rgb, dtype=np.float32) / 255.0
    return cv2.cvtColor(normalized.reshape(1, -1, 3), cv2.COLOR_RGB2LAB).reshape(-1, 3)


def _parse_color(value: str) -> tuple[float, float, float]:
    text = value.strip()
    if text.startswith("#") and len(text) == 7:
        try:
            channels = tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))
        except ValueError as error:
            raise argparse.ArgumentTypeError(f"invalid color: {value}") from error
    else:
        try:
            channels = tuple(int(part.strip()) for part in text.split(","))
        except ValueError as error:
            raise argparse.ArgumentTypeError(f"invalid color: {value}") from error
        if len(channels) != 3:
            raise argparse.ArgumentTypeError("color must be auto, #RRGGBB, or R,G,B")
    if any(channel < 0 or channel > 255 for channel in channels):
        raise argparse.ArgumentTypeError(f"color channel out of range: {value}")
    return tuple(float(channel) for channel in channels)


def _parse_region(value: str) -> tuple[int, int, int, int]:
    try:
        region = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "watermark region must be X,Y,WIDTH,HEIGHT in display pixels"
        ) from error
    if len(region) != 4 or any(number < 0 for number in region[:2]) or any(
        number <= 0 for number in region[2:]
    ):
        raise argparse.ArgumentTypeError(
            "watermark region must be X,Y,WIDTH,HEIGHT with positive dimensions"
        )
    return region


def _working_size(width: int, height: int) -> tuple[int, int]:
    if width <= height:
        return 512, max(1, int(round(height * 512.0 / width)))
    return max(1, int(round(width * 512.0 / height))), 512


def _target_size(width: int, height: int, short_edge: int) -> tuple[int, int]:
    if short_edge < 4 or short_edge > 512 or short_edge % 4:
        raise PipelineError(
            "UNSUPPORTED_INPUT",
            "target short edge must be divisible by four and within [4, 512]",
            {"target_short_edge": short_edge},
        )
    if width <= height:
        return short_edge, max(1, int(round(height * short_edge / width)))
    return max(1, int(round(width * short_edge / height))), short_edge


def _background_distance(
    image_rgb: np.ndarray,
    colors: Sequence[tuple[float, float, float]],
) -> tuple[np.ndarray, np.ndarray]:
    height, width = image_rgb.shape[:2]
    image_lab = _rgb_to_lab(image_rgb.reshape(-1, 3)).reshape(height, width, 3)
    centers_lab = _rgb_to_lab(np.asarray(colors, dtype=np.float32))
    distances = np.linalg.norm(
        image_lab[:, :, None, :] - centers_lab[None, None, :, :],
        axis=3,
    )
    nearest = np.argmin(distances, axis=2)
    return np.take_along_axis(distances, nearest[:, :, None], axis=2)[:, :, 0], nearest


def estimate_background(
    image_rgb: np.ndarray,
    *,
    border_width: int,
    tolerance: float,
) -> tuple[tuple[float, float, float], float, float]:
    height, width = image_rgb.shape[:2]
    if border_width < 1 or border_width * 2 > min(height, width):
        raise PipelineError("BACKGROUND_ESTIMATION_FAILED", "border width does not fit the frame")
    border = np.zeros((height, width), dtype=bool)
    border[:border_width] = True
    border[-border_width:] = True
    border[:, :border_width] = True
    border[:, -border_width:] = True
    samples = image_rgb[border]
    lab = _rgb_to_lab(samples)
    bin_size = max(2.0, min(6.0, tolerance * 0.35))
    quantized = np.floor(lab / bin_size).astype(np.int32)
    _, inverse, counts = np.unique(quantized, axis=0, return_inverse=True, return_counts=True)
    winning = int(np.flatnonzero(counts == counts.max())[0])
    seed = lab[inverse == winning].mean(axis=0)
    distances = np.linalg.norm(lab - seed, axis=1)
    radius = max(3.0, tolerance * 0.55)
    members = distances <= radius
    if int(np.count_nonzero(members)) < max(16, int(len(samples) * 0.80)):
        raise PipelineError(
            "UNSUPPORTED_BACKGROUND",
            "frame boundary is not explained by one near-solid color cluster",
            {"explained_fraction": float(np.mean(members))},
        )
    color = tuple(float(value) for value in samples[members].astype(np.float64).mean(axis=0))
    nearest, _ = _background_distance(image_rgb, (color,))
    border_distances = nearest[border]
    return color, float(np.mean(border_distances <= tolerance)), float(np.percentile(border_distances, 95))


def _edge_connected(candidate: np.ndarray) -> np.ndarray:
    _, labels = cv2.connectedComponents(candidate.astype(np.uint8), connectivity=8)
    edge_labels = np.unique(
        np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    )
    return np.isin(labels, edge_labels[edge_labels != 0])


def _interior_background(
    distance: np.ndarray,
    *,
    tolerance: float,
    seed_tolerance: float,
) -> np.ndarray:
    candidate = distance <= tolerance
    seeds = distance <= seed_tolerance
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        seeds.astype(np.uint8), connectivity=8
    )
    edge_labels = set(
        int(value)
        for value in np.unique(
            np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
        )
    )
    maximum_seed_area = max(4, int(distance.size * 0.05))
    interior_seed = np.zeros(distance.shape, dtype=bool)
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if label not in edge_labels and 2 <= area <= maximum_seed_area:
            interior_seed |= labels == label
    # Grow only a bounded antialiasing collar around a high-confidence enclosed
    # seed. This clears real background pockets without admitting a similarly
    # colored foreground region merely because its shape looks hole-like.
    grown = interior_seed.copy()
    kernel = np.ones((3, 3), dtype=np.uint8)
    for _ in range(6):
        grown = cv2.dilate(grown.astype(np.uint8), kernel).astype(bool) & candidate
    return grown


def _smoothstep(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def cutout_frame(
    image_rgb: np.ndarray,
    *,
    background_colors: Sequence[tuple[float, float, float]],
    tolerance: float,
    feather_width: float,
    decontaminate: float,
    residual_p95: float,
    background_mode: str = "edge-connected",
) -> tuple[np.ndarray, dict[str, float | int]]:
    distance, nearest_index = _background_distance(image_rgb, background_colors)
    # The public tolerance describes background variation. A wider matte band
    # is needed to recover antialiasing that is a mixture of foreground and
    # background rather than classifying those pixels as opaque foreground.
    matte_tolerance = min(64.0, tolerance * 2.0)
    if background_mode == "global":
        interior = np.zeros(distance.shape, dtype=bool)
        background = distance <= matte_tolerance
        seed_tolerance = 0.0
        transparent_radius = tolerance
    elif background_mode == "edge-connected":
        connected = _edge_connected(distance <= matte_tolerance)
        seed_tolerance = max(1.5, min(tolerance * 0.30, residual_p95 * 2.5))
        interior = _interior_background(
            distance,
            tolerance=min(100.0, tolerance * 4.0),
            seed_tolerance=seed_tolerance,
        )
        background = connected | interior
        transparent_radius = max(1.0, min(tolerance * 0.10, residual_p95 * 1.25))
    else:
        raise PipelineError(
            "BACKGROUND_ESTIMATION_FAILED",
            "unknown background connectivity mode",
            {"background_mode": background_mode},
        )
    normalized = (distance - transparent_radius) / max(
        matte_tolerance - transparent_radius, 1e-6
    )
    alpha = np.ones(distance.shape, dtype=np.float32)
    alpha[background] = _smoothstep(normalized[background])
    if feather_width > 0:
        radius = max(1, int(math.ceil(feather_width * 1.5)))
        smoothed = cv2.GaussianBlur(
            alpha,
            (radius * 2 + 1, radius * 2 + 1),
            sigmaX=max(0.1, feather_width / 3.0),
            borderType=cv2.BORDER_REPLICATE,
        )
        transition = background & (distance > transparent_radius) & (distance < matte_tolerance)
        alpha[transition] = smoothed[transition]
    alpha_u8 = np.rint(np.clip(alpha, 0.0, 1.0) * 255.0).astype(np.uint8)
    clean = image_rgb.astype(np.float32).copy()
    clean[alpha_u8 == 0] = 0
    partial = (alpha_u8 > 0) & (alpha_u8 < 255)
    if decontaminate > 0 and np.any(partial):
        backgrounds = np.asarray(background_colors, dtype=np.float32)[nearest_index]
        alpha_float = alpha_u8.astype(np.float32) / 255.0
        unmixed = (
            clean - (1.0 - alpha_float[:, :, None]) * backgrounds
        ) / np.maximum(alpha_float[:, :, None], 1.0 / 255.0)
        clean[partial] = clean[partial] * (1.0 - decontaminate) + np.clip(
            unmixed[partial], 0.0, 255.0
        ) * decontaminate
    rgba = np.dstack((np.rint(clean).astype(np.uint8), alpha_u8))
    retained = interior & (distance <= transparent_radius) & (alpha_u8 > 8)
    return rgba, {
        "background_seed_tolerance": seed_tolerance,
        "background_mode": background_mode,
        "matte_tolerance": matte_tolerance,
        "interior_component_pixels": int(np.count_nonzero(interior)),
        "retained_background_seed_count": int(np.count_nonzero(retained)),
    }


def suppress_detached_artifacts(
    rgba: np.ndarray,
    *,
    proximity: float = 12.0,
    maximum_area_ratio: float = 0.0025,
) -> tuple[np.ndarray, dict[str, int]]:
    binary = rgba[:, :, 3] >= 128
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary.astype(np.uint8), connectivity=8
    )
    if count <= 2:
        return rgba, {"removed_component_count": 0, "removed_pixel_count": 0}
    main_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    main_area = int(stats[main_label, cv2.CC_STAT_AREA])
    main_mask = labels == main_label
    distance_to_main = cv2.distanceTransform(
        (~main_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    removable: list[int] = []
    ambiguous: list[dict[str, object]] = []
    for label in range(1, count):
        if label == main_label:
            continue
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        right = x + int(stats[label, cv2.CC_STAT_WIDTH]) - 1
        bottom = y + int(stats[label, cv2.CC_STAT_HEIGHT]) - 1
        gap = max(0.0, float(np.min(distance_to_main[labels == label])) - 1.0)
        if gap <= proximity:
            continue
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area <= max(4, int(round(main_area * maximum_area_ratio))):
            removable.append(label)
        else:
            ambiguous.append(
                {"label": label, "area": area, "gap": gap, "bbox": [x, y, right, bottom]}
            )
    if ambiguous:
        raise PipelineError(
            "CUTOUT_QUALITY_FAILED",
            "multiple separated foreground regions cannot be attributed safely",
            {"components": ambiguous},
        )
    if not removable:
        return rgba, {"removed_component_count": 0, "removed_pixel_count": 0}
    removed_binary = np.isin(labels, removable)
    kept_binary = binary & ~removed_binary
    kernel = np.ones((3, 3), dtype=np.uint8)
    removed_support = cv2.dilate(removed_binary.astype(np.uint8), kernel, iterations=4).astype(bool)
    kept_support = cv2.dilate(kept_binary.astype(np.uint8), kernel, iterations=2).astype(bool)
    clear = removed_support & ~kept_support
    output = rgba.copy()
    output[clear] = 0
    return output, {
        "removed_component_count": len(removable),
        "removed_pixel_count": int(np.count_nonzero(clear)),
    }


def suppress_resize_islands(
    rgba: np.ndarray, *, proximity: float = 2.0
) -> tuple[np.ndarray, dict[str, int]]:
    visible = rgba[:, :, 3] > 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        visible.astype(np.uint8), connectivity=8
    )
    if count <= 2:
        return rgba, {"removed_resize_island_count": 0, "removed_resize_island_pixels": 0}
    main_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    main_mask = labels == main_label
    distance_to_main = cv2.distanceTransform(
        (~main_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    removable: list[int] = []
    for label in range(1, count):
        if label == main_label:
            continue
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        right = x + int(stats[label, cv2.CC_STAT_WIDTH]) - 1
        bottom = y + int(stats[label, cv2.CC_STAT_HEIGHT]) - 1
        component_peak_alpha = int(rgba[:, :, 3][labels == label].max())
        gap = max(0.0, float(np.min(distance_to_main[labels == label])) - 1.0)
        if component_peak_alpha <= 4 or gap > proximity:
            removable.append(label)
    output = rgba.copy()
    remove = np.isin(labels, removable)
    output[remove] = 0
    return output, {
        "removed_resize_island_count": len(removable),
        "removed_resize_island_pixels": int(np.count_nonzero(remove)),
    }


def suppress_low_alpha_haze(
    rgba: np.ndarray, *, core_alpha: int = 16, proximity: float = 2.0
) -> tuple[np.ndarray, dict[str, int]]:
    visible = rgba[:, :, 3] > 0
    core = rgba[:, :, 3] >= core_alpha
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        core.astype(np.uint8), connectivity=8
    )
    if count <= 1:
        return rgba, {"removed_low_alpha_haze_pixels": 0}
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    main_mask = labels == main
    distance_to_main = cv2.distanceTransform(
        (~main_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    keep = {main}
    for label in range(1, count):
        if label == main:
            continue
        gap = max(0.0, float(np.min(distance_to_main[labels == label])) - 1.0)
        if gap <= proximity:
            keep.add(label)
    kept_core = np.isin(labels, list(keep))
    radius = max(1, int(math.ceil(proximity)))
    support = cv2.dilate(
        kept_core.astype(np.uint8),
        np.ones((radius * 2 + 1, radius * 2 + 1), dtype=np.uint8),
    ).astype(bool)
    clear = visible & ~support
    output = rgba.copy()
    output[clear] = 0
    return output, {"removed_low_alpha_haze_pixels": int(np.count_nonzero(clear))}


def _exterior(alpha: np.ndarray) -> np.ndarray:
    transparent = alpha < 128
    _, labels = cv2.connectedComponents(transparent.astype(np.uint8), connectivity=8)
    edge_labels = np.unique(
        np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    )
    return np.isin(labels, edge_labels[edge_labels != 0])


def estimate_outline_color(rgba_frames: Sequence[np.ndarray]) -> tuple[int, int, int]:
    estimates: list[np.ndarray] = []
    for rgba in rgba_frames:
        alpha = rgba[:, :, 3]
        exterior = _exterior(alpha)
        distance = cv2.distanceTransform(
            (~exterior).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        samples = rgba[:, :, :3][(alpha >= 200) & (distance <= 3.0)]
        if len(samples) < 16:
            raise PipelineError("OUTLINE_COLOR_UNCERTAIN", "not enough outer contour pixels")
        luminance = (
            samples[:, 0].astype(np.float32) * 0.2126
            + samples[:, 1].astype(np.float32) * 0.7152
            + samples[:, 2].astype(np.float32) * 0.0722
        )
        darkest = samples[luminance <= np.quantile(luminance, 0.30)]
        estimates.append(np.median(darkest, axis=0))
    estimates_array = np.stack(estimates)
    spread = np.max(estimates_array, axis=0) - np.min(estimates_array, axis=0)
    if float(np.max(spread)) > 24.0:
        raise PipelineError(
            "OUTLINE_COLOR_UNCERTAIN",
            "outer contour color varies too much across the cycle",
            {"channel_spread": spread.tolist()},
        )
    return tuple(int(value) for value in np.rint(np.median(estimates_array, axis=0)))


def outline_color_distance(
    color: tuple[int, int, int], reference: tuple[int, int, int]
) -> float:
    colors = np.asarray((color, reference), dtype=np.float32)
    lab = _rgb_to_lab(colors)
    return float(np.linalg.norm(lab[0] - lab[1]))


def estimate_outline_reference(path: Path) -> tuple[int, int, int]:
    if not path.is_file():
        raise PipelineError(
            "OUTLINE_COLOR_UNCERTAIN",
            "outline reference is not a readable file",
            {"name": path.name},
        )
    try:
        with Image.open(path) as image:
            rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    except (OSError, ValueError) as error:
        raise PipelineError(
            "OUTLINE_COLOR_UNCERTAIN",
            "outline reference is not a readable raster image",
            {"name": path.name},
        ) from error
    return estimate_outline_color((rgba,))


def add_outline(
    rgba: np.ndarray,
    *,
    width: float,
    color: tuple[int, int, int],
    supersample: int = 4,
) -> np.ndarray:
    if width <= 0:
        raise PipelineError("OUTLINE_CLIPPED", "outline width must be positive")
    height, image_width = rgba.shape[:2]
    foreground = rgba[:, :, 3] >= 128
    coordinates = np.argwhere(foreground)
    if not len(coordinates):
        raise PipelineError("CUTOUT_QUALITY_FAILED", "cutout contains no foreground")
    y_min, x_min = coordinates.min(axis=0)
    y_max, x_max = coordinates.max(axis=0)
    margin = min(x_min, y_min, image_width - 1 - x_max, height - 1 - y_max)
    if margin < math.ceil(width + 1.0):
        raise PipelineError(
            "OUTLINE_CLIPPED",
            "working canvas has insufficient transparent margin for the outline",
            {"minimum_margin": int(margin), "outline_width": width},
        )
    exterior = _exterior(rgba[:, :, 3])
    high_size = (image_width * supersample, height * supersample)
    foreground_high = cv2.resize(
        foreground.astype(np.uint8), high_size, interpolation=cv2.INTER_NEAREST
    )
    exterior_high = cv2.resize(
        exterior.astype(np.uint8), high_size, interpolation=cv2.INTER_NEAREST
    ).astype(bool)
    distance = cv2.distanceTransform(
        (1 - foreground_high).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    coverage_high = np.clip(width * supersample + 0.5 - distance, 0.0, 1.0)
    coverage_high[~exterior_high] = 0.0
    coverage = cv2.resize(
        coverage_high, (image_width, height), interpolation=cv2.INTER_AREA
    ).astype(np.float32)
    source_alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    behind_alpha = coverage * (1.0 - source_alpha)
    output_alpha = source_alpha + behind_alpha
    numerator = rgba[:, :, :3].astype(np.float32) * source_alpha[:, :, None]
    numerator += np.asarray(color, dtype=np.float32) * behind_alpha[:, :, None]
    output_rgb = np.zeros_like(rgba[:, :, :3], dtype=np.float32)
    visible = output_alpha > 0
    output_rgb[visible] = numerator[visible] / output_alpha[visible, None]
    output = np.dstack(
        (
            np.rint(np.clip(output_rgb, 0.0, 255.0)).astype(np.uint8),
            np.rint(np.clip(output_alpha, 0.0, 1.0) * 255.0).astype(np.uint8),
        )
    )
    output[output[:, :, 3] == 0, :3] = 0
    return output


def _resize_float(channel: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(
        Image.fromarray(np.asarray(channel, dtype=np.float32), mode="F").resize(
            size, Image.Resampling.LANCZOS
        ),
        dtype=np.float32,
    )


def resize_premultiplied(rgba: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    source = rgba.astype(np.float32) / 255.0
    alpha = source[:, :, 3]
    premultiplied = source[:, :, :3] * alpha[:, :, None]
    resized_alpha = np.clip(_resize_float(alpha, size), 0.0, 1.0)
    resized_premultiplied = np.stack(
        [_resize_float(premultiplied[:, :, channel], size) for channel in range(3)],
        axis=2,
    )
    resized_premultiplied = np.clip(
        resized_premultiplied, 0.0, resized_alpha[:, :, None]
    )
    rgb = np.zeros_like(resized_premultiplied)
    visible = resized_alpha > 0
    rgb[visible] = resized_premultiplied[visible] / resized_alpha[visible, None]
    alpha_u8 = np.rint(resized_alpha * 255.0).astype(np.uint8)
    rgb_u8 = np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    rgb_u8[alpha_u8 == 0] = 0
    return np.dstack((rgb_u8, alpha_u8))


def _bbox(alpha: np.ndarray) -> tuple[int, int, int, int] | None:
    coordinates = np.argwhere(alpha >= 128)
    if not len(coordinates):
        return None
    y_min, x_min = coordinates.min(axis=0)
    y_max, x_max = coordinates.max(axis=0)
    return int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1)


def frame_metrics(
    rgba: np.ndarray,
    *,
    background_colors: Sequence[tuple[float, float, float]],
    retained_background_seed_count: int,
    outline_width: float,
) -> FrameMetrics:
    alpha = rgba[:, :, 3]
    rgb = rgba[:, :, :3]
    border = np.concatenate((alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]))
    exterior = _exterior(alpha)
    internal = (alpha <= 8) & ~exterior
    count, _, _, _ = cv2.connectedComponentsWithStats(
        internal.astype(np.uint8), connectivity=8
    )
    foreground_area = float(alpha.astype(np.float64).sum() / 255.0)
    exterior_distance = cv2.distanceTransform(
        (~exterior).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    outer_edge = (alpha >= 16) & (exterior_distance <= 4.0)
    background_distance, _ = _background_distance(rgb, background_colors)
    background_like = outer_edge & (background_distance <= 8.0)
    outer_edge_count = int(np.count_nonzero(outer_edge))
    background_like_count = int(np.count_nonzero(background_like))
    transparent = alpha == 0
    coordinates = np.argwhere(alpha >= 128)
    clipped = True
    if len(coordinates):
        y_min, x_min = coordinates.min(axis=0)
        y_max, x_max = coordinates.max(axis=0)
        margin = min(x_min, y_min, rgba.shape[1] - 1 - x_max, rgba.shape[0] - 1 - y_max)
        clipped = bool(margin < math.ceil(outline_width + 1.0))
    return FrameMetrics(
        boundary_residual_rate=float(np.mean(border > 8)),
        outer_edge_background_like_pixel_count=background_like_count,
        outer_edge_background_like_ratio=(
            background_like_count / outer_edge_count if outer_edge_count else 0.0
        ),
        transparent_rgb_nonzero_count=int(
            np.count_nonzero(np.any(rgb[transparent] != 0, axis=1))
        ),
        foreground_area=foreground_area,
        foreground_area_ratio=foreground_area / alpha.size,
        foreground_bbox=_bbox(alpha),
        partial_alpha_pixel_count=int(np.count_nonzero((alpha > 0) & (alpha < 255))),
        retained_background_seed_count=retained_background_seed_count,
        internal_hole_count=max(0, count - 1),
        clipped_outline=clipped,
    )


def _pair_metrics(left: np.ndarray, right: np.ndarray) -> dict[str, float]:
    left_float = left.astype(np.float32) / 255.0
    right_float = right.astype(np.float32) / 255.0
    left_binary = left >= 128
    right_binary = right >= 128
    union = int(np.count_nonzero(left_binary | right_binary))
    left_area = float(left_float.sum())
    right_area = float(right_float.sum())
    return {
        "mean_alpha_difference": float(np.mean(np.abs(left_float - right_float))),
        "contour_change_ratio": (
            int(np.count_nonzero(left_binary ^ right_binary)) / union if union else 0.0
        ),
        "area_change_ratio": abs(left_area - right_area)
        / max((left_area + right_area) / 2.0, 1.0),
    }


def animation_quality(alphas: Sequence[np.ndarray]) -> dict[str, object]:
    pairs = [
        {
            "from_frame": index,
            "to_frame": index + 1,
            "is_loop": False,
            **_pair_metrics(alphas[index], alphas[index + 1]),
        }
        for index in range(len(alphas) - 1)
    ]
    loop = {
        "from_frame": len(alphas) - 1,
        "to_frame": 0,
        "is_loop": True,
        **_pair_metrics(alphas[-1], alphas[0]),
    }
    metric_names = (
        "mean_alpha_difference",
        "contour_change_ratio",
        "area_change_ratio",
    )
    statistics: dict[str, dict[str, float]] = {}
    materiality = {
        "mean_alpha_difference": 0.015,
        "contour_change_ratio": 0.040,
        "area_change_ratio": 0.015,
    }
    for name in metric_names:
        values = np.asarray([pair[name] for pair in pairs], dtype=np.float64)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        statistics[name] = {"median": median, "mad": mad, "robust_scale": 1.4826 * mad}
    failures: list[dict[str, object]] = []
    for pair in pairs + [loop]:
        reasons: list[str] = []
        for name in metric_names:
            value = float(pair[name])
            scale = statistics[name]["robust_scale"]
            median = statistics[name]["median"]
            robust_outlier = (
                value > median + 1e-6
                if scale <= 1e-12
                else (value - median) / scale > 6.0
            )
            anomalous = robust_outlier and value > materiality[name]
            if anomalous:
                reasons.append(f"{name}={value:.8f} exceeds robust sequence envelope")
        if reasons:
            failures.append(
                {
                    "from_frame": pair["from_frame"],
                    "to_frame": pair["to_frame"],
                    "is_loop": pair["is_loop"],
                    "reasons": reasons,
                }
            )
    return {
        "pairs": pairs,
        "loop_pair": loop,
        "statistics": statistics,
        "materiality_floors": materiality,
        "failures": failures,
    }


def collapse_near_duplicate_frames(
    alphas: Sequence[np.ndarray],
    timings: Sequence[dict[str, float]],
    *,
    source_start_frame: int,
) -> tuple[list[int], list[dict[str, float]], dict[str, object]]:
    if len(alphas) != len(timings) or not alphas:
        raise PipelineError(
            "TEMPORAL_QUALITY_FAILED",
            "cadence collapse requires matching non-empty frames and timing records",
        )
    groups: list[list[int]] = [[0]]
    comparisons: list[dict[str, object]] = []
    for index in range(1, len(alphas)):
        metrics = _pair_metrics(alphas[index - 1], alphas[index])
        collapsed = (
            metrics["mean_alpha_difference"]
            <= CADENCE_COLLAPSE_THRESHOLDS["maximum_mean_alpha_difference"]
            and metrics["contour_change_ratio"]
            <= CADENCE_COLLAPSE_THRESHOLDS["maximum_contour_change_ratio"]
            and metrics["area_change_ratio"]
            <= CADENCE_COLLAPSE_THRESHOLDS["maximum_area_change_ratio"]
        )
        comparisons.append(
            {
                "from_source_frame": source_start_frame + index - 1,
                "to_source_frame": source_start_frame + index,
                "collapsed": collapsed,
                **metrics,
            }
        )
        if collapsed:
            groups[-1].append(index)
        else:
            groups.append([index])
    retained_indices = [group[0] for group in groups]
    merged_timings = [
        {
            "timestamp": float(timings[group[0]]["timestamp"]),
            "duration": float(sum(timings[index]["duration"] for index in group)),
        }
        for group in groups
    ]
    source_duration = float(sum(record["duration"] for record in timings))
    output_duration = float(sum(record["duration"] for record in merged_timings))
    record = {
        "schema": CADENCE_COLLAPSE_SCHEMA,
        "source_frame_count": len(alphas),
        "output_frame_count": len(retained_indices),
        "source_frame_groups": [
            [source_start_frame + index for index in group] for group in groups
        ],
        "thresholds": CADENCE_COLLAPSE_THRESHOLDS,
        "comparisons": comparisons,
        "source_duration_seconds": source_duration,
        "output_duration_seconds": output_duration,
    }
    return retained_indices, merged_timings, record


def _write_png(path: Path, rgba: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", compress_level=9)


def _write_sheet(
    path: Path,
    frames: Sequence[np.ndarray],
    *,
    columns: int,
) -> dict[str, int]:
    if columns < 1:
        raise PipelineError("UNSUPPORTED_INPUT", "sheet columns must be positive")
    height, width = frames[0].shape[:2]
    rows = int(math.ceil(len(frames) / columns))
    sheet = Image.new("RGBA", (width * columns, height * rows), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.paste(
            Image.fromarray(frame, mode="RGBA"),
            ((index % columns) * width, (index // columns) * height),
        )
    sheet.save(path, format="PNG", compress_level=9)
    return {
        "columns": columns,
        "rows": rows,
        "cell_width": width,
        "cell_height": height,
        "width": sheet.width,
        "height": sheet.height,
    }


def _write_apng(path: Path, frames: Sequence[np.ndarray], durations: Sequence[float]) -> None:
    images = [Image.fromarray(frame, mode="RGBA") for frame in frames]
    milliseconds = [max(1, int(round(duration * 1000.0))) for duration in durations]
    images[0].save(
        path,
        format="PNG",
        save_all=True,
        append_images=images[1:],
        duration=milliseconds,
        loop=0,
        disposal=2,
        blend=0,
        compress_level=9,
    )


def _checker(width: int, height: int) -> np.ndarray:
    y, x = np.indices((height, width))
    values = np.where((((x // 16) + (y // 16)) % 2)[:, :, None] == 0, 218, 166)
    return np.repeat(values.astype(np.uint8), 3, axis=2)


def _composite(rgba: np.ndarray, background: np.ndarray) -> np.ndarray:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    return np.rint(rgba[:, :, :3] * alpha + background * (1.0 - alpha)).astype(np.uint8)


def _write_inspection(
    directory: Path,
    sources: Sequence[np.ndarray],
    cutouts: Sequence[np.ndarray],
    outlined: Sequence[np.ndarray],
    final: Sequence[np.ndarray],
) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    selected = np.linspace(0, len(final) - 1, min(10, len(final)), dtype=int)
    height, width = outlined[0].shape[:2]
    canvas = Image.new("RGB", (width * len(selected), height * 3), (32, 32, 32))
    checker = _checker(width, height)
    for column, index in enumerate(selected):
        source = sources[index]
        if source.shape[:2] != (height, width):
            source = np.asarray(
                Image.fromarray(source, mode="RGB").resize((width, height), Image.Resampling.LANCZOS)
            )
        canvas.paste(Image.fromarray(source, mode="RGB"), (column * width, 0))
        canvas.paste(
            Image.fromarray(_composite(cutouts[index], checker), mode="RGB"),
            (column * width, height),
        )
        canvas.paste(
            Image.fromarray(_composite(outlined[index], checker), mode="RGB"),
            (column * width, height * 2),
        )
    overview = directory / "overview.png"
    canvas.save(overview, format="PNG", compress_level=9)

    alpha_sheet = Image.new("L", (width * len(selected), height), 0)
    for column, index in enumerate(selected):
        alpha_sheet.paste(
            Image.fromarray(cutouts[index][:, :, 3], mode="L"),
            (column * width, 0),
        )
    alpha_path = directory / "alpha-contact-sheet.png"
    alpha_sheet.save(alpha_path, format="PNG", compress_level=9)

    final_height, final_width = final[0].shape[:2]
    backgrounds = (
        ("black", np.zeros((final_height, final_width, 3), dtype=np.uint8)),
        ("white", np.full((final_height, final_width, 3), 255, dtype=np.uint8)),
        ("gray", np.full((final_height, final_width, 3), 128, dtype=np.uint8)),
        ("checker", _checker(final_width, final_height)),
    )
    composites = Image.new(
        "RGB",
        (final_width * len(selected), final_height * len(backgrounds)),
        (0, 0, 0),
    )
    for row, (_, background) in enumerate(backgrounds):
        for column, index in enumerate(selected):
            composites.paste(
                Image.fromarray(_composite(final[index], background), mode="RGB"),
                (column * final_width, row * final_height),
            )
    composites_path = directory / "multi-background-contact-sheet.png"
    composites.save(composites_path, format="PNG", compress_level=9)

    detail_size = 256
    details = Image.new("RGB", (detail_size * len(selected), detail_size), (32, 32, 32))
    for column, index in enumerate(selected):
        box = _bbox(outlined[index][:, :, 3])
        if box is None:
            continue
        x, y, box_width, box_height = box
        padding = max(8, int(round(min(box_width, box_height) * 0.08)))
        left = max(0, x - padding)
        top = max(0, y - padding)
        right = min(width, x + box_width + padding)
        bottom = min(height, y + box_height + padding)
        crop = outlined[index][top:bottom, left:right]
        crop_height, crop_width = crop.shape[:2]
        scale = min(detail_size / crop_width, detail_size / crop_height)
        resized = resize_premultiplied(
            crop, (max(1, int(round(crop_width * scale))), max(1, int(round(crop_height * scale))))
        )
        background = _checker(resized.shape[1], resized.shape[0])
        tile = Image.new("RGB", (detail_size, detail_size), (128, 128, 128))
        rendered = Image.fromarray(_composite(resized, background), mode="RGB")
        tile.paste(rendered, ((detail_size - rendered.width) // 2, (detail_size - rendered.height) // 2))
        details.paste(tile, (column * detail_size, 0))
    details_path = directory / "edge-details.png"
    details.save(details_path, format="PNG", compress_level=9)

    seam = Image.new("RGB", (final_width * 4, final_height), (32, 32, 32))
    final_checker = _checker(final_width, final_height)
    seam_tiles = (
        _composite(final[-1], final_checker),
        _composite(final[0], final_checker),
        np.repeat(final[-1][:, :, 3:4], 3, axis=2),
        np.repeat(final[0][:, :, 3:4], 3, axis=2),
    )
    for index, tile in enumerate(seam_tiles):
        seam.paste(Image.fromarray(tile, mode="RGB"), (index * final_width, 0))
    seam_path = directory / "loop-seam.png"
    seam.save(seam_path, format="PNG", compress_level=9)
    return {
        "overview": str(overview.name),
        "alpha_contact_sheet": str(alpha_path.name),
        "multi_background_contact_sheet": str(composites_path.name),
        "edge_details": str(details_path.name),
        "loop_seam": str(seam_path.name),
    }


def _mask_metrics(predicted_alpha: np.ndarray, truth_alpha: np.ndarray) -> dict[str, float]:
    predicted = predicted_alpha >= 128
    truth = truth_alpha >= 128
    true_positive = int(np.count_nonzero(predicted & truth))
    false_positive = int(np.count_nonzero(predicted & ~truth))
    false_negative = int(np.count_nonzero(~predicted & truth))
    union = true_positive + false_positive + false_negative
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = true_positive / precision_denominator if precision_denominator else 1.0
    recall = true_positive / recall_denominator if recall_denominator else 1.0
    iou = true_positive / union if union else 1.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    alpha_mae = float(
        np.mean(np.abs(predicted_alpha.astype(np.float32) - truth_alpha.astype(np.float32)))
        / 255.0
    )
    kernel = np.ones((3, 3), dtype=np.uint8)
    predicted_boundary = predicted & ~cv2.erode(predicted.astype(np.uint8), kernel).astype(bool)
    truth_boundary = truth & ~cv2.erode(truth.astype(np.uint8), kernel).astype(bool)
    if np.any(predicted_boundary) and np.any(truth_boundary):
        to_truth = cv2.distanceTransform(
            (~truth_boundary).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        to_predicted = cv2.distanceTransform(
            (~predicted_boundary).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        boundary_error = float(
            (to_truth[predicted_boundary].mean() + to_predicted[truth_boundary].mean()) / 2.0
        )
    else:
        boundary_error = float("inf")
    return {
        "iou": iou,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "alpha_mae": alpha_mae,
        "boundary_error_px": boundary_error,
    }


SYNTHETIC_THRESHOLDS = {
    "minimum_iou": 0.965,
    "minimum_precision": 0.980,
    "minimum_recall": 0.980,
    "minimum_f1": 0.980,
    "maximum_alpha_mae": 0.018,
    "maximum_boundary_error_px": 2.0,
}


def _synthetic_cases() -> list[tuple[str, np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(20260815)
    cases: list[tuple[str, np.ndarray, np.ndarray]] = []
    specifications = (
        ("bright", (242, 244, 238), "solid"),
        ("dark", (14, 18, 24), "solid"),
        ("saturated", (30, 200, 82), "noise"),
        ("gradient", (132, 138, 145), "gradient"),
        ("close", (205, 82, 118), "solid"),
    )
    scale = 4
    size = 128
    for name, background_color, background_kind in specifications:
        layer = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.ellipse((18 * scale, 10 * scale, 110 * scale, 116 * scale), fill=(38, 72, 218, 255))
        draw.rectangle((38 * scale, 50 * scale, 90 * scale, 108 * scale), fill=(225, 65, 55, 255))
        draw.line(
            ((14 * scale, 108 * scale), (114 * scale, 30 * scale)),
            fill=(25, 20, 30, 255),
            width=2 * scale,
        )
        draw.ellipse((54 * scale, 55 * scale, 74 * scale, 77 * scale), fill=(0, 0, 0, 0))
        near = tuple(min(255, value + 7) for value in background_color)
        draw.rectangle((27 * scale, 62 * scale, 35 * scale, 76 * scale), fill=near + (255,))
        truth = np.asarray(layer.resize((size, size), Image.Resampling.LANCZOS), dtype=np.uint8)
        background = np.broadcast_to(
            np.asarray(background_color, dtype=np.float32), (size, size, 3)
        ).copy()
        if background_kind == "noise":
            background += rng.normal(0.0, 1.1, size=background.shape)
        elif background_kind == "gradient":
            background += np.linspace(-2.0, 2.0, size, dtype=np.float32)[None, :, None]
        background = np.clip(background, 0.0, 255.0)
        alpha = truth[:, :, 3:4].astype(np.float32) / 255.0
        composite = truth[:, :, :3].astype(np.float32) * alpha + background * (1.0 - alpha)
        cases.append((name, np.rint(composite).astype(np.uint8), truth))
    return cases


def synthetic_quality(
    *,
    tolerance: float,
    border_width: int,
    feather_width: float,
    decontaminate: float,
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for name, composite, truth in _synthetic_cases():
        color, confidence, residual = estimate_background(
            composite, border_width=border_width, tolerance=tolerance
        )
        predicted, _ = cutout_frame(
            composite,
            background_colors=(color,),
            tolerance=tolerance,
            feather_width=feather_width,
            decontaminate=decontaminate,
            residual_p95=residual,
        )
        metrics = _mask_metrics(predicted[:, :, 3], truth[:, :, 3])
        reasons: list[str] = []
        for metric in ("iou", "precision", "recall", "f1"):
            threshold = float(SYNTHETIC_THRESHOLDS[f"minimum_{metric}"])
            if metrics[metric] < threshold:
                reasons.append(f"{metric} {metrics[metric]:.6f} below {threshold:.6f}")
        for metric in ("alpha_mae", "boundary_error_px"):
            threshold = float(SYNTHETIC_THRESHOLDS[f"maximum_{metric}"])
            if metrics[metric] > threshold:
                reasons.append(f"{metric} {metrics[metric]:.6f} above {threshold:.6f}")
        record = {
            "name": name,
            "background_confidence": confidence,
            "metrics": metrics,
            "failures": reasons,
        }
        records.append(record)
        if reasons:
            failures.append({"case": name, "reasons": reasons})
    aggregate = {
        "worst_iou": min(float(record["metrics"]["iou"]) for record in records),
        "worst_precision": min(float(record["metrics"]["precision"]) for record in records),
        "worst_recall": min(float(record["metrics"]["recall"]) for record in records),
        "worst_f1": min(float(record["metrics"]["f1"]) for record in records),
        "worst_alpha_mae": max(float(record["metrics"]["alpha_mae"]) for record in records),
        "worst_boundary_error_px": max(
            float(record["metrics"]["boundary_error_px"]) for record in records
        ),
    }
    return {
        "seed": 20260815,
        "case_count": len(records),
        "thresholds": SYNTHETIC_THRESHOLDS,
        "aggregate": aggregate,
        "cases": records,
        "passed": not failures,
        "failures": failures,
    }


def _seconds_to_frame(records: Sequence[dict[str, float]], seconds: float) -> int:
    return min(
        range(len(records)),
        key=lambda index: abs(records[index]["timestamp"] - seconds),
    )


def _remote_foreground_mask(
    image_rgb: np.ndarray,
    *,
    background_tolerance: float,
    border_width: int,
) -> tuple[np.ndarray, int]:
    color, _, residual = estimate_background(
        image_rgb,
        border_width=border_width,
        tolerance=background_tolerance,
    )
    rgba, _ = cutout_frame(
        image_rgb,
        background_colors=(color,),
        tolerance=background_tolerance,
        feather_width=1.5,
        decontaminate=1.0,
        residual_p95=residual,
    )
    foreground = rgba[:, :, 3] >= 128
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        foreground.astype(np.uint8), connectivity=8
    )
    if count <= 1:
        return np.zeros(foreground.shape, dtype=bool), 0
    dominant_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    dominant_area = int(stats[dominant_label, cv2.CC_STAT_AREA])
    dominant_mask = labels == dominant_label
    distance_to_dominant = cv2.distanceTransform(
        (~dominant_mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )
    remote = foreground & (labels != dominant_label)
    remote_labels = np.unique(labels[remote])
    for label in remote_labels:
        if label == 0:
            continue
        gap = max(0.0, float(np.min(distance_to_dominant[labels == label])) - 1.0)
        if int(stats[label, cv2.CC_STAT_AREA]) < 4 or gap <= 12.0:
            remote[labels == label] = False
    return remote, dominant_area


def analyze_watermarks(
    frames: Sequence[np.ndarray],
    *,
    frame_indices: Sequence[int],
    display_size: tuple[int, int],
    background_tolerance: float,
    border_width: int,
) -> dict[str, object]:
    if len(frames) != len(frame_indices):
        raise ValueError("watermark sample frames and indices must have equal lengths")
    if not frames:
        return {
            "status": "ambiguous",
            "coordinate_space": "display_pixels",
            "candidates": [],
            "analyzed_frame_count": 0,
            "reason": "no frames were available for watermark review",
        }
    remote_masks: list[np.ndarray] = []
    dominant_areas: list[int] = []
    successful_indices: list[int] = []
    failed_frames: list[int] = []
    for frame_index, frame in zip(frame_indices, frames, strict=True):
        try:
            remote, dominant_area = _remote_foreground_mask(
                frame,
                background_tolerance=background_tolerance,
                border_width=border_width,
            )
        except PipelineError:
            failed_frames.append(frame_index)
            continue
        remote_masks.append(remote)
        dominant_areas.append(dominant_area)
        successful_indices.append(frame_index)
    if not remote_masks:
        return {
            "status": "ambiguous",
            "coordinate_space": "display_pixels",
            "candidates": [],
            "analyzed_frame_count": 0,
            "failed_frames": failed_frames,
            "reason": "background analysis could not support watermark review",
        }
    combined = np.logical_or.reduce(remote_masks)
    merge_gap = max(5, int(round(min(combined.shape) * 0.04)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (merge_gap, merge_gap))
    grouped = cv2.dilate(combined.astype(np.uint8), kernel)
    group_count, group_labels = cv2.connectedComponents(grouped, connectivity=8)
    display_width, display_height = display_size
    scale_x = display_width / combined.shape[1]
    scale_y = display_height / combined.shape[0]
    region_padding = max(2, int(math.ceil(min(display_width, display_height) * 0.005)))
    candidates: list[dict[str, object]] = []
    maximum_dominant_area = max(dominant_areas, default=1)
    for label in range(1, group_count):
        pixels = combined & (group_labels == label)
        ys, xs = np.nonzero(pixels)
        if not len(xs):
            continue
        area = int(len(xs))
        left = max(0, int(math.floor(int(xs.min()) * scale_x)) - region_padding)
        top = max(0, int(math.floor(int(ys.min()) * scale_y)) - region_padding)
        right = min(
            display_width,
            int(math.ceil((int(xs.max()) + 1) * scale_x)) + region_padding,
        )
        bottom = min(
            display_height,
            int(math.ceil((int(ys.max()) + 1) * scale_y)) + region_padding,
        )
        sampled_hits = [
            frame_index
            for frame_index, mask in zip(successful_indices, remote_masks, strict=True)
            if np.any(mask & (group_labels == label))
        ]
        candidates.append(
            {
                "region": [left, top, right - left, bottom - top],
                "first_frame": min(sampled_hits),
                "last_frame": max(sampled_hits),
                "frame_count": len(sampled_hits),
                "frame_coverage": len(sampled_hits) / len(remote_masks),
                "foreground_area_ratio": area / maximum_dominant_area,
                "padding_pixels": region_padding,
            }
        )
    candidates.sort(key=lambda item: tuple(item["region"]))
    status = "detected" if candidates else "clear"
    return {
        "status": status,
        "coordinate_space": "display_pixels",
        "candidates": candidates,
        "analyzed_frame_count": len(successful_indices),
        "analyzed_frame_range": [successful_indices[0], successful_indices[-1]],
        "failed_frames": failed_frames,
    }


def constrain_watermark_review_to_regions(
    review: dict[str, object],
    regions: Sequence[tuple[int, int, int, int]],
) -> dict[str, object]:
    if review.get("status") == "ambiguous":
        return review
    candidates = review.get("candidates")
    if not isinstance(candidates, list):
        return review

    def intersects(candidate: object) -> bool:
        if not isinstance(candidate, dict):
            return False
        candidate_region = candidate.get("region")
        if not isinstance(candidate_region, list) or len(candidate_region) != 4:
            return False
        left, top, width, height = (int(value) for value in candidate_region)
        right = left + width
        bottom = top + height
        for region_left, region_top, region_width, region_height in regions:
            region_right = region_left + region_width
            region_bottom = region_top + region_height
            if (
                left < region_right
                and right > region_left
                and top < region_bottom
                and bottom > region_top
            ):
                return True
        return False

    scoped = [candidate for candidate in candidates if intersects(candidate)]
    ignored = [candidate for candidate in candidates if not intersects(candidate)]
    return {
        **review,
        "status": "detected" if scoped else "clear",
        "scope": "reviewed_regions",
        "reviewed_regions": [list(region) for region in regions],
        "candidates": scoped,
        "ignored_outside_reviewed_regions": ignored,
    }


def remove_watermarks(
    frames: Sequence[np.ndarray],
    *,
    regions: Sequence[tuple[int, int, int, int]],
    background_tolerance: float,
    border_width: int,
) -> tuple[list[np.ndarray], dict[str, object]]:
    cleaned_frames: list[np.ndarray] = []
    frame_records: list[dict[str, int]] = []
    total_removed = 0
    for frame_index, frame in enumerate(frames):
        height, width = frame.shape[:2]
        region_mask = np.zeros((height, width), dtype=bool)
        for x, y, region_width, region_height in regions:
            if x + region_width > width or y + region_height > height:
                raise PipelineError(
                    "WATERMARK_REGION_INVALID",
                    "watermark region lies outside the display frame",
                    {
                        "frame_size": [width, height],
                        "region": [x, y, region_width, region_height],
                    },
                )
            region_mask[y : y + region_height, x : x + region_width] = True
        color, _, residual = estimate_background(
            frame,
            border_width=min(border_width, max(1, min(height, width) // 4)),
            tolerance=background_tolerance,
        )
        rgba, _ = cutout_frame(
            frame,
            background_colors=(color,),
            tolerance=background_tolerance,
            feather_width=1.5,
            decontaminate=1.0,
            residual_p95=residual,
        )
        foreground = rgba[:, :, 3] >= 128
        count, labels, stats, _ = cv2.connectedComponentsWithStats(
            foreground.astype(np.uint8), connectivity=8
        )
        if count > 1:
            dominant_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            if np.any(region_mask & (labels == dominant_label)):
                raise PipelineError(
                    "WATERMARK_OVERLAPS_SUBJECT",
                    "reviewed watermark region overlaps the dominant subject",
                    {"frame": frame_index},
                )
        distance, _ = _background_distance(frame, (color,))
        cleaned = frame.copy()
        removed_pixels = 0
        repair_records: list[dict[str, object]] = []
        for x, y, region_width, region_height in regions:
            touches_boundary = (
                x == 0
                or y == 0
                or x + region_width == width
                or y + region_height == height
            )
            if touches_boundary:
                donor_candidates: list[tuple[str, int, int]] = []
                if x >= region_width:
                    donor_candidates.append(("left", x - region_width, y))
                if x + region_width * 2 <= width:
                    donor_candidates.append(("right", x + region_width, y))
                if y >= region_height:
                    donor_candidates.append(("up", x, y - region_height))
                if y + region_height * 2 <= height:
                    donor_candidates.append(("down", x, y + region_height))
                ranked_donors: list[tuple[float, str, int, int]] = []
                for direction, donor_x, donor_y in donor_candidates:
                    donor_foreground = foreground[
                        donor_y : donor_y + region_height,
                        donor_x : donor_x + region_width,
                    ]
                    if np.any(donor_foreground):
                        continue
                    donor_distance = distance[
                        donor_y : donor_y + region_height,
                        donor_x : donor_x + region_width,
                    ]
                    ranked_donors.append(
                        (
                            float(np.percentile(donor_distance, 95)),
                            direction,
                            donor_x,
                            donor_y,
                        )
                    )
                if not ranked_donors:
                    raise PipelineError(
                        "WATERMARK_REMOVAL_FAILED",
                        "boundary watermark region has no subject-free donor background",
                        {"frame": frame_index, "region": [x, y, region_width, region_height]},
                    )
                _, direction, donor_x, donor_y = min(ranked_donors)
                donor = frame[
                    donor_y : donor_y + region_height,
                    donor_x : donor_x + region_width,
                ].astype(np.float64)
                local_left = max(0, min(x, donor_x) - 8)
                local_top = max(0, min(y, donor_y) - 8)
                local_right = min(width, max(x, donor_x) + region_width + 8)
                local_bottom = min(height, max(y, donor_y) + region_height + 8)
                local_valid = (~foreground & ~region_mask)[
                    local_top:local_bottom, local_left:local_right
                ]
                local_y, local_x = np.nonzero(local_valid)
                local_x = local_x + local_left
                local_y = local_y + local_top
                if len(local_x) >= 16:
                    design = np.column_stack(
                        (
                            local_x.astype(np.float64),
                            local_y.astype(np.float64),
                            np.ones(len(local_x), dtype=np.float64),
                        )
                    )
                    samples = frame[local_y, local_x].astype(np.float64)
                    coefficients, _, _, _ = np.linalg.lstsq(design, samples, rcond=None)
                    patch_y, patch_x = np.indices((region_height, region_width))
                    donor_design = np.stack(
                        (
                            patch_x + donor_x,
                            patch_y + donor_y,
                            np.ones_like(patch_x),
                        ),
                        axis=2,
                    ).astype(np.float64)
                    target_design = np.stack(
                        (patch_x + x, patch_y + y, np.ones_like(patch_x)), axis=2
                    ).astype(np.float64)
                    donor_plane = donor_design @ coefficients
                    target_plane = target_design @ coefficients
                    repaired = np.clip(target_plane + donor - donor_plane, 0.0, 255.0).astype(
                        np.uint8
                    )
                    smooth_background = np.clip(target_plane, 0.0, 255.0).astype(np.uint8)
                else:
                    repaired = donor.astype(np.uint8)
                    smooth_background = np.broadcast_to(
                        np.rint(color).astype(np.uint8), repaired.shape
                    )
                collar = min(4, region_width, region_height)
                if x == 0:
                    repaired[:, :collar] = smooth_background[:, :collar]
                if x + region_width == width:
                    repaired[:, -collar:] = smooth_background[:, -collar:]
                if y == 0:
                    repaired[:collar] = smooth_background[:collar]
                if y + region_height == height:
                    repaired[-collar:] = smooth_background[-collar:]
                cleaned[y : y + region_height, x : x + region_width] = repaired
                removed_pixels += region_width * region_height
                repair_records.append(
                    {
                        "region": [x, y, region_width, region_height],
                        "method": "subject-free-donor-patch",
                        "donor": [donor_x, donor_y, region_width, region_height],
                    }
                )
                continue
            local_region = np.zeros((height, width), dtype=bool)
            local_region[y : y + region_height, x : x + region_width] = True
            removal_threshold = max(2.0, residual * 1.5)
            removal_mask = local_region & (distance > removal_threshold)
            if np.any(removal_mask):
                removal_mask = cv2.dilate(
                    removal_mask.astype(np.uint8), np.ones((5, 5), dtype=np.uint8)
                ).astype(bool) & local_region
            local_removed = int(np.count_nonzero(removal_mask))
            if local_removed:
                cleaned = cv2.inpaint(
                    cleaned,
                    (removal_mask.astype(np.uint8) * 255),
                    3.0,
                    cv2.INPAINT_TELEA,
                )
            removed_pixels += local_removed
            repair_records.append(
                {
                    "region": [x, y, region_width, region_height],
                    "method": "background-constrained-inpaint",
                    "removed_pixel_count": local_removed,
                }
            )
        total_removed += removed_pixels
        cleaned_frames.append(cleaned)
        frame_records.append(
            {
                "frame": frame_index,
                "removed_pixel_count": removed_pixels,
                "repairs": repair_records,
            }
        )
    if total_removed == 0:
        raise PipelineError(
            "WATERMARK_NOT_FOUND",
            "reviewed watermark regions contain no removable foreground",
        )
    return cleaned_frames, {
        "method": "reviewed-background-repair/v1",
        "regions": [list(region) for region in regions],
        "removed_pixel_count": total_removed,
        "frames": frame_records,
    }


def _artifact_hashes(output: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "job.json":
            hashes[str(path.relative_to(output))] = _sha256(path)
    return hashes


def _parameter_payload(args: argparse.Namespace) -> dict[str, object]:
    outline_reference = None
    if args.outline_reference is not None:
        reference_path = args.outline_reference.resolve()
        if not reference_path.is_file():
            raise PipelineError(
                "OUTLINE_COLOR_UNCERTAIN",
                "outline reference is not a readable file",
                {"name": reference_path.name},
            )
        outline_reference = {
            "name": reference_path.name,
            "sha256": _sha256(reference_path),
        }
    return {
        "target_short_edge": args.target_short_edge,
        "sheet_columns": args.sheet_columns,
        "background": args.background or ["auto"],
        "background_tolerance": args.background_tolerance,
        "background_mode": args.background_mode,
        "watermark_background_tolerance": args.watermark_background_tolerance,
        "border_width": args.border_width,
        "feather_width": args.feather_width,
        "decontaminate": args.decontaminate,
        "outline_width": args.outline_width,
        "outline_color": args.outline_color,
        "outline_reference": outline_reference,
        "outline_reference_max_distance": args.outline_reference_max_distance,
        "video_stream": args.video_stream,
        "cycle_start": args.cycle_start,
        "cycle_end": args.cycle_end,
        "watermark_action": args.watermark_action,
        "watermark_regions": args.watermark_region or [],
        "watermark_removal_authorized": args.watermark_removal_authorized,
        "collapse_near_duplicate_frames": args.collapse_near_duplicate_frames,
    }


def run_pipeline(args: argparse.Namespace) -> int:
    input_path = args.input.resolve()
    output = args.output.resolve()
    info = inspect_video(input_path, requested_stream=args.video_stream)
    parameters = _parameter_payload(args)
    watermark_background_tolerance = (
        args.watermark_background_tolerance
        if args.watermark_background_tolerance is not None
        else args.background_tolerance
    )
    if args.watermark_action == "remove" and not args.watermark_removal_authorized:
        raise PipelineError(
            "WATERMARK_AUTHORIZATION_REQUIRED",
            "watermark removal requires explicit confirmation that the caller is authorized",
        )
    if args.watermark_action == "remove" and not args.watermark_region:
        raise PipelineError(
            "WATERMARK_REGION_REQUIRED",
            "watermark removal requires at least one reviewed --watermark-region",
        )
    if args.watermark_action == "reject" and (
        args.watermark_region or args.watermark_removal_authorized
    ):
        raise PipelineError(
            "UNSUPPORTED_INPUT",
            "watermark regions and authorization require --watermark-action remove",
        )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "video": asdict(info),
                    "parameters": parameters,
                    "working_size": _working_size(info.display_width, info.display_height),
                    "final_size": _target_size(
                        info.display_width, info.display_height, args.target_short_edge
                    ),
                },
                indent=2,
            )
        )
        return 0
    if output.exists() and any(output.iterdir()):
        if not args.resume:
            raise PipelineError(
                "OUTPUT_VERIFICATION_FAILED",
                "output directory is non-empty; use a new directory or --resume",
            )
        job_path = output / "job.json"
        if not job_path.is_file():
            raise PipelineError("OUTPUT_VERIFICATION_FAILED", "resume requires job.json")
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if job.get("input", {}).get("sha256") != info.sha256 or job.get("parameters") != parameters:
            raise PipelineError(
                "OUTPUT_VERIFICATION_FAILED",
                "resume input hash or parameters do not match the existing job",
            )
        return verify_output(output)
    output.mkdir(parents=True, exist_ok=True)
    analysis_directory = output / "analysis"
    selected_directory = output / "frames" / "selected-source"
    cutout_directory = output / "frames" / "cutout-high-res"
    outlined_directory = output / "frames" / "outlined-high-res"
    final_directory = output / "frames" / "final"
    for directory in (
        analysis_directory,
        selected_directory,
        cutout_directory,
        outlined_directory,
        final_directory,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    _write_json(analysis_directory / "video.json", asdict(info))
    with tempfile.TemporaryDirectory(prefix="video-to-spritesheet-") as temporary:
        decoded_paths, timestamps = decode_video(input_path, info, Path(temporary))
        watermark_sample_indices = list(range(len(decoded_paths)))
        watermark_sample_frames: list[np.ndarray] = []
        for index in watermark_sample_indices:
            with Image.open(decoded_paths[index]) as image:
                sample = np.asarray(image.convert("RGB"), dtype=np.uint8)
            watermark_sample_frames.append(
                np.asarray(
                    Image.fromarray(sample, mode="RGB").resize(
                        _working_size(info.display_width, info.display_height),
                        Image.Resampling.LANCZOS,
                    ),
                    dtype=np.uint8,
                )
            )
        watermark_review = analyze_watermarks(
            watermark_sample_frames,
            frame_indices=watermark_sample_indices,
            display_size=(info.display_width, info.display_height),
            background_tolerance=watermark_background_tolerance,
            border_width=args.border_width,
        )
        watermark_record: dict[str, object] = {
            "schema": "video-to-spritesheet-watermark/v1",
            "passed": watermark_review["status"] == "clear",
            "action": args.watermark_action,
            "authorization": (
                "SUPPLIED" if args.watermark_removal_authorized else "UNRESOLVED"
            ),
            "regions": [list(region) for region in (args.watermark_region or [])],
            "pre_removal_review": watermark_review,
            "removal": None,
            "post_removal_review": None,
        }
        _write_json(analysis_directory / "watermark.json", watermark_record)
        if watermark_review["status"] == "ambiguous":
            raise PipelineError(
                "WATERMARK_REVIEW_FAILED",
                "watermark review is ambiguous; inspect the source before running the pipeline",
                {"watermark_review": watermark_review},
            )
        if watermark_review["status"] == "detected" and args.watermark_action == "reject":
            raise PipelineError(
                "WATERMARK_DETECTED",
                "potential watermark content was detected; review it before authorized removal",
                {"watermark_review": watermark_review},
            )
        candidates = find_cycle_candidates(decoded_paths)
        _write_json(
            analysis_directory / "cycle-candidates.json",
            {"candidates": [asdict(candidate) for candidate in candidates[:100]]},
        )
        explicit_start = (
            _seconds_to_frame(timestamps, args.cycle_start)
            if args.cycle_start is not None
            else None
        )
        explicit_end = (
            _seconds_to_frame(timestamps, args.cycle_end)
            if args.cycle_end is not None
            else None
        )
        selected = select_cycle(
            candidates,
            frame_count=len(decoded_paths),
            explicit_start=explicit_start,
            explicit_end=explicit_end,
        )
        selected_paths = decoded_paths[selected.start_frame : selected.end_frame + 1]
        selected_timestamps = timestamps[selected.start_frame : selected.end_frame + 1]
        _write_json(
            analysis_directory / "selected-cycle.json",
            {
                **asdict(selected),
                "start_timestamp": selected_timestamps[0]["timestamp"],
                "end_timestamp": selected_timestamps[-1]["timestamp"],
                "frames": selected_timestamps,
            },
        )
        source_frames: list[np.ndarray] = []
        for source_path in selected_paths:
            with Image.open(source_path) as image:
                source_rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            source_frames.append(source_rgb)
        if args.watermark_action == "remove":
            source_frames, removal = remove_watermarks(
                source_frames,
                regions=args.watermark_region,
                background_tolerance=watermark_background_tolerance,
                border_width=args.border_width,
            )
            post_indices = list(range(len(source_frames)))
            post_frames = [
                np.asarray(
                    Image.fromarray(source_frames[index], mode="RGB").resize(
                        _working_size(info.display_width, info.display_height),
                        Image.Resampling.LANCZOS,
                    ),
                    dtype=np.uint8,
                )
                for index in post_indices
            ]
            post_review = analyze_watermarks(
                post_frames,
                frame_indices=post_indices,
                display_size=(info.display_width, info.display_height),
                background_tolerance=watermark_background_tolerance,
                border_width=args.border_width,
            )
            post_review = constrain_watermark_review_to_regions(
                post_review, args.watermark_region
            )
            watermark_record["removal"] = removal
            watermark_record["post_removal_review"] = post_review
            watermark_record["passed"] = post_review["status"] == "clear"
            _write_json(analysis_directory / "watermark.json", watermark_record)
            if post_review["status"] != "clear":
                raise PipelineError(
                    "WATERMARK_REMOVAL_FAILED",
                    "watermark candidates remain after removal",
                    {"watermark_review": post_review},
                )
        for index, source_rgb in enumerate(source_frames):
            Image.fromarray(source_rgb, mode="RGB").save(
                selected_directory / f"frame-{index:04d}.png", format="PNG", compress_level=9
            )

    working_size = _working_size(info.display_width, info.display_height)
    final_size = _target_size(info.display_width, info.display_height, args.target_short_edge)
    normalized_frames = [
        np.asarray(
            Image.fromarray(frame, mode="RGB").resize(working_size, Image.Resampling.LANCZOS),
            dtype=np.uint8,
        )
        for frame in source_frames
    ]
    explicit_backgrounds: tuple[tuple[float, float, float], ...] | None = None
    if args.background and args.background != ["auto"]:
        if "auto" in [value.lower() for value in args.background]:
            raise PipelineError(
                "BACKGROUND_ESTIMATION_FAILED",
                "background auto cannot be combined with explicit colors",
            )
        explicit_backgrounds = tuple(_parse_color(value) for value in args.background)
    cutouts: list[np.ndarray] = []
    frame_records: list[dict[str, object]] = []
    frame_failures: list[dict[str, object]] = []
    for index, frame in enumerate(normalized_frames):
        if explicit_backgrounds is None:
            color, confidence, residual = estimate_background(
                frame,
                border_width=args.border_width,
                tolerance=args.background_tolerance,
            )
            colors: Sequence[tuple[float, float, float]] = (color,)
        else:
            colors = explicit_backgrounds
            distance, _ = _background_distance(frame, colors)
            border = np.zeros(distance.shape, dtype=bool)
            border[: args.border_width] = True
            border[-args.border_width :] = True
            border[:, : args.border_width] = True
            border[:, -args.border_width :] = True
            confidence = float(np.mean(distance[border] <= args.background_tolerance))
            residual = float(np.percentile(distance[border], 95))
        rgba, diagnostics = cutout_frame(
            frame,
            background_colors=colors,
            tolerance=args.background_tolerance,
            feather_width=args.feather_width,
            decontaminate=args.decontaminate,
            residual_p95=residual,
            background_mode=args.background_mode,
        )
        rgba, detached_diagnostics = suppress_detached_artifacts(
            rgba, proximity=max(12.0, args.outline_width * 2.0)
        )
        diagnostics.update(detached_diagnostics)
        rgba, visible_island_diagnostics = suppress_resize_islands(rgba, proximity=2.0)
        diagnostics.update(
            {
                "removed_cutout_island_count": visible_island_diagnostics[
                    "removed_resize_island_count"
                ],
                "removed_cutout_island_pixels": visible_island_diagnostics[
                    "removed_resize_island_pixels"
                ],
            }
        )
        metrics = frame_metrics(
            rgba,
            background_colors=colors,
            retained_background_seed_count=int(diagnostics["retained_background_seed_count"]),
            outline_width=args.outline_width,
        )
        reasons: list[str] = []
        if confidence < 0.90:
            reasons.append(f"background confidence {confidence:.6f} below 0.900000")
        if metrics.boundary_residual_rate > 0.001:
            reasons.append("boundary background residue exceeds 0.001")
        if metrics.outer_edge_background_like_ratio > 0.12:
            reasons.append(
                "outer-edge background-like color ratio exceeds 0.120000"
            )
        if metrics.retained_background_seed_count:
            reasons.append("enclosed high-confidence background seeds remain opaque")
        if metrics.transparent_rgb_nonzero_count:
            reasons.append("transparent RGB is nonzero")
        if metrics.clipped_outline:
            reasons.append("working canvas cannot contain the requested outline")
        if reasons:
            frame_failures.append({"frame": index, "reasons": reasons})
        _write_png(cutout_directory / f"frame-{index:04d}.png", rgba)
        cutouts.append(rgba)
        frame_records.append(
            {
                "index": index,
                "background_colors": colors,
                "background_confidence": confidence,
                "background_residual_p95": residual,
                "cutout_diagnostics": diagnostics,
                "metrics": asdict(metrics),
                "failures": reasons,
            }
        )
    synthetic = synthetic_quality(
        tolerance=args.background_tolerance,
        border_width=min(args.border_width, 12),
        feather_width=args.feather_width,
        decontaminate=args.decontaminate,
    )
    if not synthetic["passed"]:
        frame_failures.append({"scope": "synthetic_truth", "reasons": synthetic["failures"]})
    if frame_failures:
        _write_json(
            output / "quality-report.json",
            {
                "schema": QUALITY_VERSION,
                "passed": False,
                "synthetic_truth": synthetic,
                "watermark": {
                    "passed": watermark_record["passed"],
                    "analysis": "analysis/watermark.json",
                },
                "frames": frame_records,
                "failures": frame_failures,
                "human_visual_review": "pending",
            },
        )
        raise PipelineError(
            "CUTOUT_QUALITY_FAILED",
            "one or more cutout quality gates failed",
            {"failures": frame_failures},
        )
    retained_indices = list(range(len(cutouts)))
    cadence_record: dict[str, object] | None = None
    output_timestamps = selected_timestamps
    if args.collapse_near_duplicate_frames:
        retained_indices, output_timestamps, cadence_record = collapse_near_duplicate_frames(
            [cutout[:, :, 3] for cutout in cutouts],
            selected_timestamps,
            source_start_frame=selected.start_frame,
        )
        if len(retained_indices) < 3:
            raise PipelineError(
                "TEMPORAL_QUALITY_FAILED",
                "cadence collapse leaves fewer than three output frames",
                {"cadence": cadence_record},
            )
        normalized_frames = [normalized_frames[index] for index in retained_indices]
        cutouts = [cutouts[index] for index in retained_indices]
    if args.outline_color.lower() == "auto":
        outline_color = estimate_outline_color(cutouts)
    else:
        parsed = _parse_color(args.outline_color)
        outline_color = tuple(int(value) for value in parsed)
    outline_reference_record: dict[str, object] | None = None
    if args.outline_reference is not None:
        reference_path = args.outline_reference.resolve()
        reference_color = estimate_outline_reference(reference_path)
        reference_distance = outline_color_distance(outline_color, reference_color)
        outline_reference_record = {
            "name": reference_path.name,
            "sha256": _sha256(reference_path),
            "estimated_color": reference_color,
            "distance": reference_distance,
            "maximum_distance": args.outline_reference_max_distance,
        }
        if reference_distance > args.outline_reference_max_distance:
            raise PipelineError(
                "OUTLINE_COLOR_MISMATCH",
                "selected outline color does not match the production reference",
                {"outline": outline_color, "reference": outline_reference_record},
            )
    outlined_frames: list[np.ndarray] = []
    final_frames: list[np.ndarray] = []
    final_frame_diagnostics: list[dict[str, int]] = []
    for index, cutout in enumerate(cutouts):
        outlined = add_outline(
            cutout,
            width=args.outline_width,
            color=outline_color,
        )
        final = resize_premultiplied(outlined, final_size)
        final, resize_diagnostics = suppress_resize_islands(final)
        final, haze_diagnostics = suppress_low_alpha_haze(final)
        _write_png(outlined_directory / f"frame-{index:04d}.png", outlined)
        _write_png(final_directory / f"frame-{index:04d}.png", final)
        outlined_frames.append(outlined)
        final_frames.append(final)
        final_frame_diagnostics.append(
            {"index": index, **resize_diagnostics, **haze_diagnostics}
        )
    temporal = animation_quality([frame[:, :, 3] for frame in final_frames])
    if temporal["failures"]:
        raise PipelineError(
            "TEMPORAL_QUALITY_FAILED",
            "alpha sequence contains robust temporal outliers",
            {"failures": temporal["failures"]},
        )
    sheet_metadata = _write_sheet(
        output / "spritesheet.png", final_frames, columns=args.sheet_columns
    )
    durations = [record["duration"] for record in output_timestamps]
    _write_apng(output / "loop-preview.png", final_frames, durations)
    inspection = _write_inspection(
        output / "inspection", normalized_frames, cutouts, outlined_frames, final_frames
    )
    quality_report = {
        "schema": QUALITY_VERSION,
        "passed": True,
        "synthetic_truth": synthetic,
        "frames": frame_records,
        "final_frame_diagnostics": final_frame_diagnostics,
        "animation": temporal,
        "outline": {
            "width": args.outline_width,
            "color": outline_color,
            "reference": outline_reference_record,
        },
        "working_size": working_size,
        "final_size": final_size,
        "spritesheet": sheet_metadata,
        "inspection": inspection,
        "watermark": {
            "passed": watermark_record["passed"],
            "analysis": "analysis/watermark.json",
        },
        "cadence": cadence_record,
        "failures": [],
        "human_visual_review": "pending",
    }
    _write_json(output / "quality-report.json", quality_report)
    job = {
        "schema": SCHEMA_VERSION,
        "status": "complete",
        "input": {"sha256": info.sha256, "name": input_path.name},
        "video": asdict(info),
        "parameters": parameters,
        "selected_cycle": asdict(selected),
        "frame_timing": output_timestamps,
        "cadence": cadence_record,
        "working_size": working_size,
        "final_size": final_size,
        "spritesheet": sheet_metadata,
        "watermark": {
            "action": args.watermark_action,
            "authorization": watermark_record["authorization"],
            "regions": watermark_record["regions"],
            "analysis": "analysis/watermark.json",
        },
        "artifacts": _artifact_hashes(output),
        "claims": {
            "machine_verification": "MACHINE-VERIFIED",
            "human_visual_review": "UNRESOLVED",
            "watermark_removal_authorization": watermark_record["authorization"],
        },
    }
    _write_json(output / "job.json", job)
    return verify_output(output)


def _read_json(path: Path, *, code: str = "OUTPUT_VERIFICATION_FAILED") -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(code, f"cannot read valid JSON: {path.name}") from error
    if not isinstance(payload, dict):
        raise PipelineError(code, f"JSON root must be an object: {path.name}")
    return payload


def verify_output(output: Path, *, emit: bool = True) -> int:
    output = output.resolve()
    job_path = output / "job.json"
    quality_path = output / "quality-report.json"
    if not job_path.is_file() or not quality_path.is_file():
        raise PipelineError(
            "OUTPUT_VERIFICATION_FAILED",
            "output is missing job.json or quality-report.json",
        )
    job = _read_json(job_path)
    quality = _read_json(quality_path)
    failures: list[dict[str, object]] = []
    if job.get("schema") != SCHEMA_VERSION or job.get("status") != "complete":
        failures.append({"artifact": "job.json", "reason": "invalid schema or status"})
    if quality.get("schema") != QUALITY_VERSION or quality.get("passed") is not True:
        failures.append(
            {"artifact": "quality-report.json", "reason": "quality report is not passing"}
        )
    quality_watermark = quality.get("watermark")
    if (
        not isinstance(quality_watermark, dict)
        or quality_watermark.get("passed") is not True
        or quality_watermark.get("analysis") != "analysis/watermark.json"
    ):
        failures.append(
            {"artifact": "quality-report.json", "reason": "invalid watermark summary"}
        )
    job_watermark = job.get("watermark")
    watermark_path = output / "analysis" / "watermark.json"
    if not isinstance(job_watermark, dict) or job_watermark.get("analysis") != (
        "analysis/watermark.json"
    ):
        failures.append({"artifact": "job.json", "reason": "invalid watermark reference"})
    elif not watermark_path.is_file():
        failures.append({"artifact": "analysis/watermark.json", "reason": "missing watermark record"})
    else:
        watermark = _read_json(watermark_path)
        action = watermark.get("action")
        if (
            watermark.get("schema") != "video-to-spritesheet-watermark/v1"
            or watermark.get("passed") is not True
            or action != job_watermark.get("action")
            or watermark.get("authorization") != job_watermark.get("authorization")
            or watermark.get("regions") != job_watermark.get("regions")
        ):
            failures.append(
                {"artifact": "analysis/watermark.json", "reason": "invalid watermark record"}
            )
        elif action == "remove":
            post_review = watermark.get("post_removal_review")
            if (
                watermark.get("authorization") != "SUPPLIED"
                or not isinstance(watermark.get("removal"), dict)
                or not isinstance(post_review, dict)
                or post_review.get("status") != "clear"
            ):
                failures.append(
                    {
                        "artifact": "analysis/watermark.json",
                        "reason": "authorized removal is not independently cleared",
                    }
                )
        elif action == "reject":
            pre_review = watermark.get("pre_removal_review")
            if not isinstance(pre_review, dict) or pre_review.get("status") != "clear":
                failures.append(
                    {
                        "artifact": "analysis/watermark.json",
                        "reason": "unremoved watermark review is not clear",
                    }
                )
        else:
            failures.append(
                {"artifact": "analysis/watermark.json", "reason": "unknown watermark action"}
            )
    expected_hashes = job.get("artifacts")
    if not isinstance(expected_hashes, dict):
        failures.append({"artifact": "job.json", "reason": "artifacts is not an object"})
        expected_hashes = {}
    actual_hashes = _artifact_hashes(output)
    if set(expected_hashes) != set(actual_hashes):
        failures.append(
            {
                "artifact": "job.json",
                "reason": "artifact closure mismatch",
                "missing": sorted(set(expected_hashes) - set(actual_hashes)),
                "unexpected": sorted(set(actual_hashes) - set(expected_hashes)),
            }
        )
    for relative, expected in expected_hashes.items():
        actual = actual_hashes.get(relative)
        if actual is not None and actual != expected:
            failures.append(
                {"artifact": relative, "reason": "sha256 mismatch", "expected": expected, "actual": actual}
            )
    timing = job.get("frame_timing", [])
    expected_count = len(timing) if isinstance(timing, list) else 0
    parameters = job.get("parameters")
    collapse_requested = (
        isinstance(parameters, dict)
        and parameters.get("collapse_near_duplicate_frames") is True
    )
    cadence = job.get("cadence")
    if collapse_requested:
        selected_cycle_path = output / "analysis" / "selected-cycle.json"
        if not isinstance(cadence, dict) or cadence.get("schema") != CADENCE_COLLAPSE_SCHEMA:
            failures.append({"artifact": "job.json", "reason": "invalid cadence record"})
        elif not selected_cycle_path.is_file():
            failures.append(
                {"artifact": "analysis/selected-cycle.json", "reason": "missing cycle record"}
            )
        else:
            selected_cycle_record = _read_json(selected_cycle_path)
            source_timing = selected_cycle_record.get("frames")
            selected_cycle = job.get("selected_cycle")
            cutout_paths = sorted(
                (output / "frames" / "cutout-high-res").glob("frame-*.png")
            )
            if (
                not isinstance(source_timing, list)
                or not isinstance(selected_cycle, dict)
                or not isinstance(selected_cycle.get("start_frame"), int)
                or len(cutout_paths) != len(source_timing)
            ):
                failures.append(
                    {"artifact": "job.json", "reason": "cadence source evidence is incomplete"}
                )
            else:
                source_alphas: list[np.ndarray] = []
                try:
                    for path in cutout_paths:
                        with Image.open(path) as image:
                            source_alphas.append(
                                np.asarray(image.convert("RGBA"), dtype=np.uint8)[:, :, 3]
                            )
                    _, expected_timing, expected_cadence = collapse_near_duplicate_frames(
                        source_alphas,
                        source_timing,
                        source_start_frame=int(selected_cycle["start_frame"]),
                    )
                except (OSError, TypeError, ValueError) as error:
                    failures.append(
                        {
                            "artifact": "frames/cutout-high-res",
                            "reason": f"cannot recompute cadence: {error}",
                        }
                    )
                else:
                    for key in (
                        "source_frame_count",
                        "output_frame_count",
                        "source_frame_groups",
                        "thresholds",
                        "comparisons",
                        "source_duration_seconds",
                        "output_duration_seconds",
                    ):
                        if cadence.get(key) != expected_cadence[key]:
                            failures.append(
                                {
                                    "artifact": "job.json",
                                    "reason": f"cadence {key} does not match source evidence",
                                }
                            )
                    if timing != expected_timing:
                        failures.append(
                            {
                                "artifact": "job.json",
                                "reason": "collapsed frame timing does not match source evidence",
                            }
                        )
    elif cadence is not None:
        failures.append(
            {"artifact": "job.json", "reason": "cadence record exists without collapse parameter"}
        )
    final_directory = output / "frames" / "final"
    final_paths = sorted(final_directory.glob("frame-*.png"))
    if len(final_paths) != expected_count or expected_count < 3:
        failures.append(
            {
                "artifact": "frames/final",
                "reason": "frame count mismatch",
                "expected": expected_count,
                "actual": len(final_paths),
            }
        )
    expected_size_value = job.get("final_size", [])
    expected_size = (
        tuple(int(value) for value in expected_size_value)
        if isinstance(expected_size_value, list) and len(expected_size_value) == 2
        else None
    )
    for path in final_paths:
        try:
            with Image.open(path) as image:
                if image.mode != "RGBA" or (expected_size and image.size != expected_size):
                    failures.append(
                        {
                            "artifact": str(path.relative_to(output)),
                            "reason": "final frame mode or size mismatch",
                            "mode": image.mode,
                            "size": list(image.size),
                        }
                    )
        except OSError as error:
            failures.append(
                {"artifact": str(path.relative_to(output)), "reason": f"unreadable PNG: {error}"}
            )
    sheet_meta = job.get("spritesheet", {})
    sheet_path = output / "spritesheet.png"
    if not isinstance(sheet_meta, dict) or not sheet_path.is_file():
        failures.append({"artifact": "spritesheet.png", "reason": "missing sheet metadata or file"})
    else:
        try:
            with Image.open(sheet_path) as sheet_image:
                sheet = np.asarray(sheet_image.convert("RGBA"), dtype=np.uint8)
                expected_sheet_size = (int(sheet_meta["width"]), int(sheet_meta["height"]))
                if sheet_image.size != expected_sheet_size:
                    failures.append({"artifact": "spritesheet.png", "reason": "sheet size mismatch"})
                columns = int(sheet_meta["columns"])
                rows = int(sheet_meta["rows"])
                cell_width = int(sheet_meta["cell_width"])
                cell_height = int(sheet_meta["cell_height"])
                for cell in range(expected_count, columns * rows):
                    x = (cell % columns) * cell_width
                    y = (cell // columns) * cell_height
                    tile = sheet[y : y + cell_height, x : x + cell_width]
                    if np.any(tile):
                        failures.append(
                            {
                                "artifact": "spritesheet.png",
                                "reason": "unused sheet cell is not fully transparent RGBA",
                                "cell": cell,
                            }
                        )
        except (KeyError, OSError, TypeError, ValueError) as error:
            failures.append({"artifact": "spritesheet.png", "reason": f"invalid sheet: {error}"})
    preview_path = output / "loop-preview.png"
    try:
        with Image.open(preview_path) as preview:
            if getattr(preview, "n_frames", 1) != expected_count:
                failures.append({"artifact": "loop-preview.png", "reason": "APNG frame count mismatch"})
            if int(preview.info.get("loop", -1)) != 0:
                failures.append({"artifact": "loop-preview.png", "reason": "APNG is not infinite-looping"})
            if expected_size and preview.size != expected_size:
                failures.append({"artifact": "loop-preview.png", "reason": "APNG size mismatch"})
    except OSError as error:
        failures.append({"artifact": "loop-preview.png", "reason": f"unreadable APNG: {error}"})
    if failures:
        raise PipelineError(
            "OUTPUT_VERIFICATION_FAILED",
            "output closure or artifact verification failed",
            {"failures": failures},
        )
    result = {
        "schema": "video-to-spritesheet-verification/v1",
        "passed": True,
        "output": str(output),
        "frame_count": expected_count,
        "final_size": list(expected_size) if expected_size else None,
        "artifact_count": len(actual_hashes),
        "human_visual_review": quality.get("human_visual_review", "pending"),
    }
    if emit:
        print(json.dumps(result, indent=2))
    return 0


def inspect_command(args: argparse.Namespace) -> int:
    path = args.input.resolve()
    info = inspect_video(path, requested_stream=args.video_stream)
    with tempfile.TemporaryDirectory(prefix="video-to-spritesheet-inspect-") as temporary:
        frames, timestamps = decode_video(path, info, Path(temporary))
        candidates = find_cycle_candidates(frames)
        sample_indices = [
            int(value)
            for value in sorted(
                set(np.linspace(0, len(frames) - 1, min(8, len(frames)), dtype=int))
            )
        ]
        background_records: list[dict[str, object]] = []
        for index in sample_indices:
            with Image.open(frames[index]) as image:
                source = np.asarray(image.convert("RGB"), dtype=np.uint8)
            normalized = np.asarray(
                Image.fromarray(source, mode="RGB").resize(
                    _working_size(info.display_width, info.display_height),
                    Image.Resampling.LANCZOS,
                ),
                dtype=np.uint8,
            )
            try:
                color, confidence, residual = estimate_background(
                    normalized, border_width=args.border_width, tolerance=args.background_tolerance
                )
                background_records.append(
                    {
                        "frame": index,
                        "color": color,
                        "confidence": confidence,
                        "residual_p95": residual,
                        "supported": confidence >= 0.90,
                    }
                )
            except PipelineError as error:
                background_records.append(
                    {"frame": index, "supported": False, "error": error.payload()["error"]}
                )
        watermark_frames: list[np.ndarray] = []
        for frame_path in frames:
            with Image.open(frame_path) as image:
                source = np.asarray(image.convert("RGB"), dtype=np.uint8)
            watermark_frames.append(
                np.asarray(
                    Image.fromarray(source, mode="RGB").resize(
                        _working_size(info.display_width, info.display_height),
                        Image.Resampling.LANCZOS,
                    ),
                    dtype=np.uint8,
                )
            )
        watermark_review = analyze_watermarks(
            watermark_frames,
            frame_indices=list(range(len(frames))),
            display_size=(info.display_width, info.display_height),
            background_tolerance=args.background_tolerance,
            border_width=args.border_width,
        )
    result = {
        "schema": "video-to-spritesheet-inspection/v1",
        "video": asdict(info),
        "decoded_frame_count": len(frames),
        "frame_timing": timestamps,
        "working_size": _working_size(info.display_width, info.display_height),
        "background_samples": background_records,
        "watermark_review": watermark_review,
        "cycle_candidates": [asdict(candidate) for candidate in candidates[:20]],
    }
    print(json.dumps(result, indent=2))
    return 0


def diagnose_command(args: argparse.Namespace) -> int:
    try:
        return verify_output(args.output, emit=True)
    except PipelineError as error:
        print(json.dumps({"diagnosis": error.payload()["error"]}, indent=2))
        return 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract one deterministic transparent looping spritesheet from a local video."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="inspect media and cycle candidates")
    inspect_parser.add_argument("--input", required=True, type=Path)
    inspect_parser.add_argument("--video-stream", type=int)
    inspect_parser.add_argument("--background-tolerance", type=float, default=22.0)
    inspect_parser.add_argument("--border-width", type=int, default=12)
    inspect_parser.set_defaults(handler=inspect_command)

    run_parser = subparsers.add_parser("run", help="run the complete verified pipeline")
    run_parser.add_argument("--input", required=True, type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.add_argument("--target-short-edge", required=True, type=int)
    run_parser.add_argument("--sheet-columns", type=int, default=4)
    run_parser.add_argument("--background", action="append")
    run_parser.add_argument("--background-tolerance", type=float, default=22.0)
    run_parser.add_argument(
        "--background-mode",
        choices=("edge-connected", "global"),
        default="edge-connected",
    )
    run_parser.add_argument("--watermark-background-tolerance", type=float)
    run_parser.add_argument("--border-width", type=int, default=12)
    run_parser.add_argument("--feather-width", type=float, default=1.5)
    run_parser.add_argument("--decontaminate", type=float, default=1.0)
    run_parser.add_argument("--outline-width", type=float, default=6.0)
    run_parser.add_argument("--outline-color", default="auto")
    run_parser.add_argument("--outline-reference", type=Path)
    run_parser.add_argument("--outline-reference-max-distance", type=float, default=6.0)
    run_parser.add_argument("--video-stream", type=int)
    run_parser.add_argument("--cycle-start", type=float)
    run_parser.add_argument("--cycle-end", type=float)
    run_parser.add_argument(
        "--watermark-action", choices=("reject", "remove"), default="reject"
    )
    run_parser.add_argument("--watermark-region", action="append", type=_parse_region)
    run_parser.add_argument("--watermark-removal-authorized", action="store_true")
    run_parser.add_argument("--collapse-near-duplicate-frames", action="store_true")
    run_parser.add_argument("--resume", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.set_defaults(handler=run_pipeline)

    for name, handler in (("verify", verify_output), ("diagnose", diagnose_command)):
        output_parser = subparsers.add_parser(name, help=f"{name} an existing output")
        output_parser.add_argument("--output", required=True, type=Path)
        if name == "verify":
            output_parser.set_defaults(handler=lambda args: verify_output(args.output))
        else:
            output_parser.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "background_tolerance", 1.0) <= 0:
        parser.error("--background-tolerance must be positive")
    if (
        getattr(args, "watermark_background_tolerance", None) is not None
        and args.watermark_background_tolerance <= 0
    ):
        parser.error("--watermark-background-tolerance must be positive")
    if getattr(args, "border_width", 1) < 1:
        parser.error("--border-width must be positive")
    if not 0.0 <= getattr(args, "decontaminate", 0.0) <= 1.0:
        parser.error("--decontaminate must be within [0, 1]")
    if getattr(args, "outline_reference_max_distance", 1.0) <= 0:
        parser.error("--outline-reference-max-distance must be positive")
    try:
        return int(args.handler(args))
    except PipelineError as error:
        print(json.dumps(error.payload(), indent=2), file=sys.stderr)
        return 3 if error.code.endswith("QUALITY_FAILED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
