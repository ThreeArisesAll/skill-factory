"""Atomic JSON and filesystem observation helpers."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_ASSET_BYTES = 64 * 1024 * 1024


class LockedJob:
    def __init__(self, job: Path):
        self.path = job.parent / f".{job.name}.production.lock"
        self.descriptor = -1

    def __enter__(self) -> Any:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        metadata = os.fstat(self.descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            os.close(self.descriptor)
            raise ValueError("job lock must be a private regular file")
        fcntl.flock(self.descriptor, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_: object) -> None:
        fcntl.flock(self.descriptor, fcntl.LOCK_UN)
        os.close(self.descriptor)


def regular_snapshot(path: Path, limit: int) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("input must be a single-link regular non-symlink file")
        if before.st_size > limit:
            raise ValueError("input exceeds the bounded size limit")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise ValueError("input exceeds the bounded size limit")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("input changed while being read")
        return b"".join(chunks), after
    finally:
        os.close(descriptor)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    data, _ = regular_snapshot(path, MAX_ASSET_BYTES)
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data, _ = regular_snapshot(path, MAX_JSON_BYTES)
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def freeze_regular(path: Path, destination: Path, limit: int = MAX_ASSET_BYTES) -> str:
    data, _ = regular_snapshot(path, limit)
    digest = hashlib.sha256(data).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{digest}{path.suffix.lower()}"
    if target.exists():
        existing, _ = regular_snapshot(target, limit)
        if existing != data:
            raise ValueError("content-addressed target does not match its digest")
        return str(target)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".frozen-", dir=destination)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o444)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_canonical_json(path: Path, value: Any) -> None:
    """Atomically write the shared canonical JSON byte representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(canonical_bytes(value))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def tree_snapshot(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    paths = [root] if root.is_file() else sorted(root.rglob("*"))
    records: list[dict[str, Any]] = []
    for path in paths:
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if path.is_symlink():
            kind = "symlink"
            digest = hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
        elif path.is_file():
            kind = "file"
            digest = sha256_file(path)
        elif path.is_dir():
            kind = "directory"
            digest = None
        else:
            kind = "other"
            digest = None
        records.append({"path": relative, "kind": kind, "sha256": digest, "mode": f"{mode:04o}"})
    return records
