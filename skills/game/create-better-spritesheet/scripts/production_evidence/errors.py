"""Stable failures for the production-evidence CLI."""

from __future__ import annotations


class EvidenceError(Exception):
    """A user-correctable evidence contract failure with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
