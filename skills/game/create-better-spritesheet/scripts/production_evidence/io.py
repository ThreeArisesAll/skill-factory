"""Canonical JSON, bounded I/O, hashes, and atomic directory helpers."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .errors import EvidenceError

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TREE_BYTES = 512 * 1024 * 1024
MAX_TREE_FILES = 4096


class BuildBudget:
    """Cumulative output-target budget; repeated sources consume repeatedly."""

    def __init__(
        self, *, max_files: int = MAX_TREE_FILES, max_bytes: int = MAX_TREE_BYTES
    ) -> None:
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.files = 0
        self.bytes = 0

    def reserve(self, byte_count: int, location: str) -> None:
        if not isinstance(byte_count, int) or byte_count < 0:
            raise EvidenceError(
                "RESOURCE_LIMIT", f"invalid build reservation for {location}"
            )
        if self.files + 1 > self.max_files or self.bytes + byte_count > self.max_bytes:
            raise EvidenceError(
                "RESOURCE_LIMIT", f"build budget exceeded before writing {location}"
            )
        self.files += 1
        self.bytes += byte_count

    def reserve_file(self, source: Path, location: str) -> None:
        metadata = source.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise EvidenceError(
                "FILE_NOT_REGULAR", f"cannot reserve non-regular input: {source}"
            )
        self.reserve(metadata.st_size, location)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON with one portable byte representation."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EvidenceError("INVALID_JSON_VALUE", str(error)) from error


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def write_canonical_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def read_json(path: Path, location: str) -> dict[str, Any]:
    if not path.is_absolute():
        raise EvidenceError("PATH_NOT_ABSOLUTE", f"{location} must be an absolute path")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_JSON_BYTES:
            os.close(descriptor)
            raise EvidenceError(
                "RESOURCE_LIMIT", f"{location} is not a bounded regular JSON file"
            )
        with os.fdopen(descriptor, "rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
            after = os.fstat(source.fileno())
        before_identity = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity or len(raw) > MAX_JSON_BYTES:
            raise EvidenceError("FILE_CHANGED", f"{location} changed while reading")
        value = json.loads(raw.decode("utf-8"))
    except EvidenceError:
        raise
    except FileNotFoundError as error:
        raise EvidenceError(
            "FILE_NOT_FOUND", f"{location} must be a regular file"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError("INVALID_JSON", f"{location}: {error}") from error
    if not isinstance(value, dict):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must contain a JSON object")
    return value


def read_bound_json_snapshot(
    path: Path, expected_sha256: str, location: str
) -> tuple[str, dict[str, Any], bytes]:
    """Read, hash, and parse one immutable bounded descriptor snapshot."""
    if not path.is_absolute():
        raise EvidenceError("PATH_NOT_ABSOLUTE", f"{location} must be an absolute path")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_JSON_BYTES:
            os.close(descriptor)
            raise EvidenceError(
                "RESOURCE_LIMIT", f"{location} is not a bounded regular JSON file"
            )
        with os.fdopen(descriptor, "rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
            after = os.fstat(source.fileno())
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if identity(before) != identity(after) or len(raw) > MAX_JSON_BYTES:
            raise EvidenceError("FILE_CHANGED", f"{location} changed while reading")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected_sha256:
            raise EvidenceError(
                "HASH_MISMATCH", f"{location} does not match its declared SHA-256"
            )
        value = json.loads(raw.decode("utf-8"))
    except EvidenceError:
        raise
    except FileNotFoundError as error:
        raise EvidenceError(
            "FILE_NOT_FOUND", f"{location} must be a regular file"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError("INVALID_JSON", f"{location}: {error}") from error
    if not isinstance(value, dict):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must contain a JSON object")
    return digest, value, raw


def require_regular_file(
    path: Path, location: str, *, max_bytes: int = MAX_FILE_BYTES
) -> Path:
    if not path.is_absolute():
        raise EvidenceError("PATH_NOT_ABSOLUTE", f"{location} must be an absolute path")
    if path.is_symlink():
        raise EvidenceError("SYMLINK_FORBIDDEN", f"{location} must not be a symlink")
    if not path.is_file():
        raise EvidenceError("FILE_NOT_FOUND", f"{location} must be a regular file")
    try:
        size = path.stat().st_size
    except OSError as error:
        raise EvidenceError(
            "FILE_IO_FAILED", f"cannot inspect {location}: {error}"
        ) from error
    if size > max_bytes:
        raise EvidenceError("RESOURCE_LIMIT", f"{location} exceeds {max_bytes} bytes")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            os.close(descriptor)
            raise EvidenceError(
                "FILE_NOT_REGULAR", f"cannot hash non-regular file: {path}"
            )
        if metadata.st_size > MAX_FILE_BYTES:
            os.close(descriptor)
            raise EvidenceError(
                "RESOURCE_LIMIT", f"file exceeds {MAX_FILE_BYTES} bytes: {path}"
            )
        with os.fdopen(descriptor, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(source.fileno())
            before_identity = (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_size,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
            )
            after_identity = (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            if after_identity != before_identity:
                raise EvidenceError(
                    "FILE_CHANGED", f"file changed while hashing: {path}"
                )
    except EvidenceError:
        raise
    except OSError as error:
        raise EvidenceError("FILE_IO_FAILED", f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def copy_bound_file(
    source: Path,
    destination: Path,
    expected_sha256: str,
    *,
    budget: BuildBudget | None = None,
    budget_location: str | None = None,
) -> str:
    """Copy and hash a bounded regular file from one O_NOFOLLOW descriptor."""
    digest = hashlib.sha256()
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE_BYTES:
        os.close(descriptor)
        raise EvidenceError(
            "RESOURCE_LIMIT", f"cannot copy unbounded or non-regular file: {source}"
        )
    if budget is not None:
        try:
            budget.reserve(metadata.st_size, budget_location or destination.as_posix())
        except BaseException:
            os.close(descriptor)
            raise
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            os.fdopen(descriptor, "rb") as input_file,
            destination.open("xb") as output_file,
        ):
            for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                digest.update(chunk)
                output_file.write(chunk)
            after = os.fstat(input_file.fileno())
        before_identity = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        copied_hash = digest.hexdigest()
        if before_identity != after_identity or copied_hash != expected_sha256:
            raise EvidenceError(
                "FILE_CHANGED", f"source changed while copying: {source}"
            )
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return copied_hash


def validate_sha256(value: Any, location: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EvidenceError("SCHEMA_INVALID", f"{location} must be a lowercase SHA-256")
    return value


def verify_file_reference(value: Any, location: str) -> tuple[Path, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location} must contain exactly path and sha256"
        )
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location}.path must be a non-empty string"
        )
    path = require_regular_file(Path(raw_path), f"{location}.path")
    expected = validate_sha256(value.get("sha256"), f"{location}.sha256")
    if sha256_file(path) != expected:
        raise EvidenceError(
            "HASH_MISMATCH", f"{location} does not match its declared SHA-256"
        )
    return path, expected


def resolve_job_reference(root: Path, value: Any, location: str) -> tuple[Path, str]:
    if not isinstance(value, dict) or set(value) != {"ref", "sha256"}:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location} must contain exactly ref and sha256"
        )
    ref = value.get("ref")
    if not isinstance(ref, str) or not ref:
        raise EvidenceError(
            "SCHEMA_INVALID", f"{location}.ref must be a non-empty string"
        )
    relative = Path(ref)
    if relative.is_absolute() or ".." in relative.parts or ref != relative.as_posix():
        raise EvidenceError(
            "PATH_ESCAPE", f"{location}.ref must be a normalized job-relative path"
        )
    path = root / relative
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise EvidenceError(
            "PATH_ESCAPE", f"{location}.ref resolves outside the job root"
        )
    cursor = resolved_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise EvidenceError(
                "SYMLINK_FORBIDDEN", f"{location}.ref traverses a symlink"
            )
    require_regular_file(resolved_path, f"{location}.ref")
    if path.is_symlink():
        raise EvidenceError(
            "SYMLINK_FORBIDDEN", f"{location}.ref must not be a symlink"
        )
    expected = validate_sha256(value.get("sha256"), f"{location}.sha256")
    if sha256_file(resolved_path) != expected:
        raise EvidenceError(
            "HASH_MISMATCH", f"{location} does not match its declared SHA-256"
        )
    return resolved_path, expected


def atomic_directory(output_dir: Path, build: Callable[[Path], None]) -> None:
    if output_dir.exists():
        raise EvidenceError(
            "OUTPUT_EXISTS", f"output directory already exists: {output_dir}"
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
    )
    try:
        build(temporary)
        libc = ctypes.CDLL(None, use_errno=True)
        rename_exclusive = getattr(libc, "renamex_np", None)
        if rename_exclusive is not None:
            rename_exclusive.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename_exclusive.restype = ctypes.c_int
            result = rename_exclusive(
                os.fsencode(temporary),
                os.fsencode(output_dir),
                ctypes.c_uint(0x00000004),
            )
            if result != 0:
                error_number = ctypes.get_errno()
                if error_number in (errno.EEXIST, errno.ENOTEMPTY):
                    raise EvidenceError(
                        "OUTPUT_EXISTS",
                        f"output directory appeared during staging: {output_dir}",
                    )
                raise OSError(error_number, os.strerror(error_number), str(output_dir))
        else:
            rename_noreplace = getattr(libc, "renameat2", None)
            if rename_noreplace is None:
                raise EvidenceError(
                    "ATOMIC_PUBLISH_UNSUPPORTED",
                    "platform lacks atomic no-replace directory publication",
                )
            rename_noreplace.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename_noreplace.restype = ctypes.c_int
            result = rename_noreplace(
                -100,
                os.fsencode(temporary),
                -100,
                os.fsencode(output_dir),
                ctypes.c_uint(1),
            )
            if result != 0:
                error_number = ctypes.get_errno()
                if error_number in (errno.EEXIST, errno.ENOTEMPTY):
                    raise EvidenceError(
                        "OUTPUT_EXISTS",
                        f"output directory appeared during staging: {output_dir}",
                    )
                raise OSError(error_number, os.strerror(error_number), str(output_dir))
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def reject_path_overlap(output_dir: Path, inputs: list[Path]) -> None:
    """Reject output/input ancestry in either direction before staging."""
    output = output_dir.resolve()
    for raw_input in inputs:
        source = raw_input.resolve()
        if (
            output == source
            or output.is_relative_to(source)
            or source.is_relative_to(output)
        ):
            raise EvidenceError(
                "PATH_OVERLAP", f"output directory overlaps input: {raw_input}"
            )


def reserve_build_budget(inputs: list[Path], derived_bytes: int = 0) -> None:
    """Reject a build before staging when its cumulative upper bound is excessive."""
    total = derived_bytes
    seen: set[tuple[int, int]] = set()
    for raw in inputs:
        entries = inspect_tree(raw) if raw.is_dir() else [raw]
        for path in entries:
            metadata = path.stat(follow_symlinks=False)
            identity = (metadata.st_dev, metadata.st_ino)
            if identity not in seen:
                seen.add(identity)
                total += metadata.st_size
            if len(seen) > MAX_TREE_FILES or total > MAX_TREE_BYTES:
                raise EvidenceError(
                    "RESOURCE_LIMIT", "build exceeds cumulative file or byte budget"
                )


def inspect_tree(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError(
            "PACKAGE_INVALID", "package root must be a non-symlink directory"
        )
    files: list[Path] = []
    total = 0
    for entry in sorted(
        root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
    ):
        if entry.is_symlink():
            raise EvidenceError(
                "SYMLINK_FORBIDDEN", f"package entry is a symlink: {entry}"
            )
        if entry.is_dir():
            continue
        if not entry.is_file():
            raise EvidenceError(
                "PACKAGE_INVALID", f"package entry is not a regular file: {entry}"
            )
        files.append(entry)
        total += entry.stat().st_size
        if len(files) > MAX_TREE_FILES or total > MAX_TREE_BYTES:
            raise EvidenceError(
                "RESOURCE_LIMIT", "package tree exceeds bounded file count or byte size"
            )
    return files


def package_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in inspect_tree(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        file_hash = bytes.fromhex(sha256_file(path))
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(file_hash)
    return digest.hexdigest()
