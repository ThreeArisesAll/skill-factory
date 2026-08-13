"""Advance recoverable production jobs and verify immutable deliveries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from production_job import advance_job, verify_subject
from production_job.contracts import ProductionError
from production_job.io import read_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    advance = subparsers.add_parser("advance", help="create, resume, or respond to one atomic job")
    advance.add_argument("--job", required=True, type=Path)
    source = advance.add_mutually_exclusive_group(required=True)
    source.add_argument("--intent", type=Path, help="spritesheet-production-intent/v1 JSON")
    source.add_argument("--response", type=Path, help="checkpoint-bound response JSON")
    advance.add_argument("--json", action="store_true", required=True)
    verify = subparsers.add_parser("verify", help="read-only verification of a package manifest or delivery directory")
    verify.add_argument("--subject", required=True, type=Path)
    verify.add_argument("--json", action="store_true", required=True)
    return parser.parse_args()


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    try:
        if args.command == "advance":
            result = advance_job(
                args.job,
                read_json(args.intent) if args.intent else None,
                read_json(args.response) if args.response else None,
            )
        else:
            result = verify_subject(args.subject)
    except ProductionError as error:
        emit({"ok": False, "error": {"code": error.code, "message": error.message, "details": error.details}})
        return 1
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        emit({"ok": False, "error": {"code": "INVALID_INPUT", "message": str(error), "details": {}}})
        return 1
    emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
