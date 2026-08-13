"""Diagnose, seal, and verify spritesheet production delivery evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from production_evidence.delivery import seal_delivery, verification_report
from production_evidence.diagnostics import diagnose
from production_evidence.errors import EvidenceError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Current schemas: identity-bible/v2, motion-plan/v2, raw-frame-admission/v1,\n"
            "motion-diagnostics/v2, review-packet/v1, spritesheet-production-delivery/v2.\n"
            "Compatibility: delivery/evidence v1 and runtime-playback-proof/v1 remain supported.\n"
            "seal-delivery consumes the delivery schema with each {ref, sha256} replaced by\n"
            "{path, sha256}, where path is an absolute regular non-symlink file."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    diagnose_parser = commands.add_parser(
        "diagnose",
        description="Verify a v5 or v4 package and deterministically emit measured diagnostics and review renderings.",
    )
    diagnose_parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="absolute spritesheet-package/v5 or v4 manifest.json",
    )
    diagnose_parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="new atomic diagnostics directory",
    )
    seal_parser = commands.add_parser(
        "seal-delivery",
        description="Validate hash-bound evidence and copy it with the verified package into a closed atomic delivery.",
    )
    seal_parser.add_argument(
        "--request",
        required=True,
        type=Path,
        help="spritesheet-production-delivery/v2 or compatible v1 request using absolute path references",
    )
    seal_parser.add_argument(
        "--output-dir", required=True, type=Path, help="new atomic delivery directory"
    )
    verify_parser = commands.add_parser(
        "verify",
        description="Verify a sealed delivery and emit a structured report without conflating evidence classifications.",
    )
    verify_parser.add_argument(
        "--delivery", required=True, type=Path, help="sealed job-relative delivery.json"
    )
    return parser.parse_args()


def _emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main() -> int:
    args = parse_args()
    pipeline_path = Path(__file__).with_name("spritesheet_pipeline.py")
    try:
        if args.command == "diagnose":
            diagnose(args.manifest.absolute(), args.output_dir.resolve(), pipeline_path)
            _emit(
                {
                    "command": "diagnose",
                    "status": "ok",
                    "output_dir": str(args.output_dir.resolve()),
                }
            )
        elif args.command == "seal-delivery":
            seal_delivery(
                args.request.absolute(), args.output_dir.resolve(), pipeline_path
            )
            _emit(
                {
                    "command": "seal-delivery",
                    "status": "ok",
                    "output_dir": str(args.output_dir.resolve()),
                }
            )
        elif args.command == "verify":
            report = verification_report(args.delivery.absolute(), pipeline_path)
            _emit(report)
            return 0 if report["passed"] else 1
        else:
            raise EvidenceError(
                "COMMAND_UNSUPPORTED", f"unsupported command: {args.command}"
            )
    except EvidenceError as error:
        _emit({"error": {"code": error.code, "message": str(error)}})
        return 2
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        _emit({"error": {"code": "INTERNAL_CONTRACT_FAILURE", "message": str(error)}})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
