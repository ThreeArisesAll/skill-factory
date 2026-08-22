# Pixel Evidence and Package v5

`spritesheet-package/v5` is the current pixel package. The package contains only admitted canonical material, concrete high-resolution frame sources, deterministic rendering evidence, logical playback metadata, and the assembled sheet.

## Public and internal boundaries

The public production seam is `spritesheet_production.py advance|verify`. The public evidence seam is `spritesheet_delivery.py diagnose|seal-delivery|verify`. `spritesheet_pipeline.py` is an internal and compatibility adapter whose commands remain available for scoped pixel-contract work.

The v5 build adapter consumes `spritesheet-production-request/v5`. Do not author this request by hand during normal production; the approved production job projects it from identity, motion-plan, source-admission, and review state.

## Package model

The v5 manifest records:

- Cell geometry, origin, anchor, safe bounds, outline contract, sampler, and frame count
- Canonical references and replayable canonical-admission material
- One artifact per unique concrete high-resolution source
- Ordered clips with `positions`, durations, events, direction, camera, loop, root-motion, transition, and terminal-hold metadata
- Hash-bound canonical, keyframe-set, and sequence approvals
- `spritesheet-rendering-receipt/v2`
- Row-major or column-major assembly cells and final sheet artifact

Each concrete position has `id == source`. An alias has a distinct logical `id`, references an earlier concrete `source` in the same clip, and declares `hold` or `closing`. The sheet contains a cell for every logical position, but the artifact table and rendering receipt contain each concrete source exactly once.

## Deterministic proof

`verify-package` independently checks:

- Closed schema, bounded resources, normalized package-relative paths, regular files, and a closed package tree
- Canonical proof replay, source hashes, decoded properties, and canonical pixels
- Clip position graph, aliases, timing, events, bracketing, review scope, and approval order
- High-resolution source hashes and transparent RGB
- Outline and premultiplied-resize replay for every concrete source
- Receipt contents, target-cell pixels, complete sheet pixels, layout, and empty unused cells in full RGBA
- Artifact reachability with no orphan or undeclared file

The verifier proves declared deterministic derivation and binding. It does not prove that a pose obeys the motion plan, that identity is aesthetically consistent, or that timing feels correct.

## Diagnostics

`motion-diagnostics/v2` provides a contact sheet, native-size board, onion-skin board, per-clip playback previews, and per-cell measurements:

- Alpha bounds and area
- Alpha centroid and anchor offset
- Safe-bounds overflow and clipped edges
- Pixel difference from the previous logical cell

During delivery verification, every v2 measurement is recomputed from exact final sheet pixels and compared to the sealed record. A changed measurement remains detectable even if an attacker updates its file hash and review-packet hash.

## Failure and recovery

Build and diagnostics outputs are atomic. A failed build, quality gate, diagnostics pass, seal, or state commit must not advance job state or leave a publishable partial result. Resume from the earliest invalid owner:

- Identity or canonical defect: canonical preparation and all descendants
- Plan defect: full motion-plan reapproval and all image descendants
- Raw-source defect: affected source admission and dependent reviews/build
- Renderer or assembly defect: rebuild package, diagnostics, package review, and delivery
- Presentation defect: regenerate presentation and package review without changing valid package bytes when possible

Never repair a manifest, receipt, cell, or sheet by hand. Regenerate it from the authoritative upstream source and contract.
