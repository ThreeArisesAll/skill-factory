"""Content-addressed and atomic package filesystem operations."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .errors import ContractError

_AT_FDCWD = -2
_RENAME_NOREPLACE = 1
_RENAME_EXCL = 0x4
DEFAULT_MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_AGGREGATE_FILE_BYTES = 512 * 1024 * 1024
MAX_AGGREGATE_DECODED_PIXELS = 256 * 1024 * 1024


@dataclass(frozen=True)
class RegularFileSnapshot:
    """Bytes and digest observed through one bounded regular-file descriptor."""

    data: bytes
    sha256: str
    size: int


@dataclass
class ResourceBudget:
    """Aggregate byte and decoded-pixel budget for one public operation."""

    max_bytes: int = MAX_AGGREGATE_FILE_BYTES
    max_decoded_pixels: int = MAX_AGGREGATE_DECODED_PIXELS
    consumed_bytes: int = 0
    consumed_decoded_pixels: int = 0

    def consume_bytes(self, size: int, location: str) -> None:
        if self.consumed_bytes + size > self.max_bytes:
            raise ContractError(
                f"{location} aggregate file bytes exceed {self.max_bytes}",
            )
        self.consumed_bytes += size

    def consume_decoded_pixels(self, pixels: int, location: str) -> None:
        if self.consumed_decoded_pixels + pixels > self.max_decoded_pixels:
            raise ContractError(
                f"{location} aggregate decoded pixels exceed {self.max_decoded_pixels}",
            )
        self.consumed_decoded_pixels += pixels


def read_regular_file_snapshot(
    path: Path,
    location: str,
    max_bytes: int,
    *,
    budget: ResourceBudget | None = None,
) -> RegularFileSnapshot:
    return _regular_file_snapshot(
        path,
        location,
        max_bytes,
        retain_data=True,
        budget=budget,
    )


def sha256_file(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_FILE_BYTES,
    location: str = "file",
    budget: ResourceBudget | None = None,
) -> str:
    return _regular_file_snapshot(
        path,
        location,
        max_bytes,
        retain_data=False,
        budget=budget,
    ).sha256


def _regular_file_snapshot(
    path: Path,
    location: str,
    max_bytes: int,
    *,
    retain_data: bool,
    budget: ResourceBudget | None,
) -> RegularFileSnapshot:
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow
    path_identity: tuple[int, int] | None = None
    if not nofollow:
        try:
            path_status = os.lstat(path)
        except OSError as error:
            raise ContractError(f"cannot read {location}: {error}") from error
        if stat.S_ISLNK(path_status.st_mode):
            raise ContractError(f"{location} must be a regular non-symlink file: {path}")
        path_identity = (path_status.st_dev, path_status.st_ino)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.EMLINK):
            raise ContractError(f"{location} must be a regular non-symlink file: {path}") from error
        raise ContractError(f"cannot read {location}: {error}") from error
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"{location} must be a regular non-symlink file: {path}")
        if path_identity is not None and path_identity != (before.st_dev, before.st_ino):
            raise ContractError(f"{location} changed while being opened")
        if before.st_size > max_bytes:
            raise ContractError(f"{location} file exceeds {max_bytes} bytes")
        if budget is not None:
            budget.consume_bytes(before.st_size, location)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ContractError(f"{location} file exceeds {max_bytes} bytes")
            digest.update(chunk)
            if retain_data:
                chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or total != after.st_size:
            raise ContractError(f"{location} changed while being read")
    except OSError as error:
        raise ContractError(f"cannot read {location}: {error}") from error
    finally:
        os.close(descriptor)
    return RegularFileSnapshot(
        data=b"".join(chunks) if retain_data else b"",
        sha256=digest.hexdigest(),
        size=total,
    )


def atomic_directory(output_dir: Path, build: Callable[[Path], None]) -> None:
    if os.path.lexists(output_dir):
        raise ContractError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))
    try:
        build(temporary)
        _commit_directory_noreplace(temporary, output_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _commit_directory_noreplace(source: Path, destination: Path) -> None:
    """Publish a directory without replacing any destination entry."""
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        result = libc.renamex_np(source_bytes, destination_bytes, _RENAME_EXCL)
        if result == 0:
            return
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise ContractError(f"output directory already exists: {destination}")
        raise OSError(error_number, os.strerror(error_number), destination)
    if hasattr(libc, "renameat2"):
        result = libc.renameat2(
            _AT_FDCWD,
            source_bytes,
            _AT_FDCWD,
            destination_bytes,
            _RENAME_NOREPLACE,
        )
        if result == 0:
            return
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise ContractError(f"output directory already exists: {destination}")
        if error_number not in (errno.ENOSYS, errno.EINVAL):
            raise OSError(error_number, os.strerror(error_number), destination)

    raise ContractError("ATOMIC_PUBLISH_UNSUPPORTED")


def image_record(
    artifact_id: str,
    artifact_type: str,
    path: str,
    image: Image.Image,
    digest: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "type": artifact_type,
        "path": path,
        "sha256": digest,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        **extra,
    }


def cell_position(index: int, columns: int, rows: int, order: str) -> tuple[int, int]:
    if order == "row-major":
        return index % columns, index // columns
    return index // rows, index % rows
