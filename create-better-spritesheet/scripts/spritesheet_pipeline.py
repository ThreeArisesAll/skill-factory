"""Build and verify deterministic spritesheet evidence packages."""

from __future__ import annotations

import argparse
from pathlib import Path

from spritesheet_core import ContractError
from spritesheet_core.admission import canonical_admission_proof
from spritesheet_core.builder import build_package
from spritesheet_core.canonical import prepare_canonical
from spritesheet_core.package_io import (
    atomic_directory,
    cell_position,
    image_record,
    sha256_file,
)
from spritesheet_core.production import (
    parse_production_request as _parse_production_request,
)
from spritesheet_core.protocol import (
    ADMISSION_PROOF_SCHEMA,
    CANONICAL_REQUEST_SCHEMA,
    CLIP_KEYS,
    CONTRACT_KEYS,
    EVIDENCE_SCHEMA,
    FORBIDDEN_TERMS,
    HIGH_RESOLUTION_SHORT_SIDE,
    IDENTITY_ALGORITHM,
    MASK_POLICY,
    NORMALIZATION_ALGORITHM,
    OUTLINE_ALGORITHM,
    OUTLINE_KEYS,
    PACKAGE_SCHEMA,
    PRODUCTION_REQUEST_SCHEMA,
    RENDERING_PIPELINE,
    RENDERING_RECEIPT_SCHEMA,
    SAMPLER,
    normalize_clip_metadata,
    read_request,
    require_absolute_path,
    require_exact_keys,
    require_object,
    require_positive_int,
    require_string,
    validate_bounds,
    validate_outline_contract,
    validate_point,
    validate_review_requests,
)
from spritesheet_core.rendering import (
    MAX_HIGH_RESOLUTION_SIDE,
    MAX_TARGET_SIDE,
    apply_outline,
    clear_transparent_rgb,
    decode_rgba,
    normalize_to_canvas,
    open_rgba,
    render_high_resolution_source,
    resize_premultiplied,
    resolve_high_resolution_dimensions,
)
from spritesheet_core.verification import verify_package, verify_package_report


def parse_production_request(request_path: Path) -> dict[str, object]:
    """Return the legacy mutable plain-dict normalized request shape."""
    parsed = dict(_parse_production_request(request_path))
    parsed.pop("artifact_bytes", None)
    return parsed


__all__ = [
    "ADMISSION_PROOF_SCHEMA",
    "CANONICAL_REQUEST_SCHEMA",
    "CLIP_KEYS",
    "CONTRACT_KEYS",
    "EVIDENCE_SCHEMA",
    "FORBIDDEN_TERMS",
    "HIGH_RESOLUTION_SHORT_SIDE",
    "IDENTITY_ALGORITHM",
    "MASK_POLICY",
    "MAX_HIGH_RESOLUTION_SIDE",
    "MAX_TARGET_SIDE",
    "NORMALIZATION_ALGORITHM",
    "OUTLINE_ALGORITHM",
    "OUTLINE_KEYS",
    "PACKAGE_SCHEMA",
    "PRODUCTION_REQUEST_SCHEMA",
    "RENDERING_PIPELINE",
    "RENDERING_RECEIPT_SCHEMA",
    "SAMPLER",
    "ContractError",
    "apply_outline",
    "atomic_directory",
    "build_package",
    "canonical_admission_proof",
    "cell_position",
    "clear_transparent_rgb",
    "decode_rgba",
    "image_record",
    "main",
    "normalize_clip_metadata",
    "normalize_to_canvas",
    "open_rgba",
    "parse_args",
    "parse_production_request",
    "prepare_canonical",
    "read_request",
    "render_high_resolution_source",
    "require_absolute_path",
    "require_exact_keys",
    "require_object",
    "require_positive_int",
    "require_string",
    "resize_premultiplied",
    "resolve_high_resolution_dimensions",
    "sha256_file",
    "validate_bounds",
    "validate_outline_contract",
    "validate_point",
    "validate_review_requests",
    "verify_package",
    "verify_package_report",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Public schemas:\n"
            "  canonical-authoring-request/v3 -> canonical review candidate + replay evidence\n"
            "  spritesheet-production-request/v4 -> admission-bound immutable spritesheet package\n"
            "  spritesheet-package/v4 -> independently replayed authoritative manifest"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser(
        "prepare-canonical",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Consume canonical-authoring-request/v3. Required fields:\n"
            "  canonical_id: production canonical-reference artifact ID\n"
            "  source: absolute path to a regular non-symlink RGBA PNG\n"
            "  target: frame_width, frame_height\n"
            "  outline: enabled, target_width, and color (RGBA array) only when enabled\n"
            "The command atomically emits a candidate, source evidence, authoring evidence, and admission proof."
        ),
    )
    prepare.add_argument("--request", required=True, type=Path, help="canonical-authoring-request/v3 JSON")
    prepare.add_argument("--output-dir", required=True, type=Path, help="new atomic candidate directory")
    build = subparsers.add_parser(
        "build-package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Consume spritesheet-production-request/v4. Required sections:\n"
            "  contract: dimensions, 512 high-resolution side, sampler, conditional outline, origin, anchor, safe bounds\n"
            "  canonical_references: id + absolute regular candidate, evidence_path, and proof_path\n"
            "  clips: runtime metadata + ordered keyframe/in-between records with absolute RGBA PNG source_path values\n"
            "  reviews: hash-bound canonical, keyframe-set, and sequence approvals\n"
            "  grid: columns + row-major or column-major order"
        ),
    )
    build.add_argument("--request", required=True, type=Path, help="spritesheet-production-request/v4 JSON")
    build.add_argument("--output-dir", required=True, type=Path, help="new atomic package directory")
    verify = subparsers.add_parser(
        "verify-package",
        description="Verify a spritesheet-package/v4 manifest, replay canonical admission and every cell, and emit MACHINE-VERIFIED, DECLARED, and REVIEWED results.",
    )
    verify.add_argument("--manifest", required=True, type=Path, help="package-relative authoritative manifest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "prepare-canonical":
            prepare_canonical(args.request, args.output_dir)
        elif args.command == "build-package":
            build_package(args.request, args.output_dir)
        elif args.command == "verify-package":
            if not verify_package(args.manifest):
                return 1
        else:
            raise ContractError(f"{args.command} is not implemented")
    except (ContractError, OSError, ValueError, TypeError, KeyError, IndexError) as error:
        print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
