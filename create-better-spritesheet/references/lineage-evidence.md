# Spritesheet Package Evidence v2

The authoritative manifest uses `spritesheet-package/v2`. The pipeline CLI and its tests are the executable source of truth for the complete JSON schema; this reference defines the stable shape, closed vocabularies, and evidence semantics without caching every request field.

## Formal lineage

The production lineage is exactly:

`ProductionSpec -> CanonicalReferenceSet -> ApprovedHighResolutionSequence -> deterministic target-cell rendering -> SpritesheetPackage`

The production artifact type vocabulary is closed:

- `canonical-reference`
- `high-resolution-frame`
- `spritesheet`

The review gate vocabulary is closed:

- `canonical-approval`
- `keyframe-set-approval`
- `sequence-approval`

Sources, candidates, unoutlined authoring buffers, action references, contact sheets, and other review evidence are not production artifacts. A target cell is a logical region of the spritesheet and has no artifact record, standalone PNG, or editable production stage. The production request and manifest use closed fields; place project-specific notes outside the package instead of adding another production branch.

## Compact manifest shape

Paths are normalized UTF-8 strings resolved relative to the manifest. Hashes are lowercase SHA-256 values over exact file bytes. Indices are zero-based. The authoritative manifest contains exactly these sections:

```text
schema_version: "spritesheet-package/v2"
contract:        dimensions, sampling, outline, animation origin, anchor, and safe bounds
artifacts:       canonical-reference, high-resolution-frame, and spritesheet records
clips:           direction, camera, playback, timing, events, and ordered frame IDs
reviews:         canonical-approval, keyframe-set-approval, and sequence-approval records
sampling:        sampler identifier and replay proof obligation
assembly:        fixed-grid layout plus direct source-to-cell mappings
```

Every artifact record has a unique ID, type, normalized package-relative path, SHA-256 hash, decoded width and height, and `RGBA` mode. Every `high-resolution-frame` also has exactly one role: `keyframe` or `in-between`, plus the applicable canonical-reference ID. In-betweens additionally identify the two adjacent approved keyframes that bracket them.

The contract records `animation_origin`, `anchor`, and `safe_bounds`. Every clip records `direction`, `camera`, `root_motion`, `transition`, `terminal_hold`, one positive duration per logical position, and indexed events.

Every canonical canvas preserves the target aspect ratio, fixes its shortest side at `512 px`, and rounds the proportional long side to the nearest integer. The target shortest side is strictly less than `512 px`, the target longest side is at most `4096 px`, and the derived high-resolution longest side is at most `16384 px`.

## Gate binding

Reviews bind content, not mutable paths or labels:

- A `canonical-approval` binds one canonical-reference SHA-256 hash.
- A `keyframe-set-approval` binds the applicable canonical hash followed by the ordered set of all keyframe hashes for one clip and direction.
- A `sequence-approval` binds the applicable canonical hash followed by the complete ordered list of high-resolution-frame hashes for one clip and direction.

Each clip has at least two keyframes and at least two in-betweens. The keyframe-set gate precedes generation of its in-betweens; the sequence gate precedes package rendering. Replacing any bound bytes invalidates that gate and every dependent result.

Human approval is review evidence. A validator can verify its structure and exact hash subjects but cannot authenticate the reviewer or observe the creative act.

## Deterministic rendering

The sampler identifier is fixed to `lanczos-premultiplied-v1`. It decodes a straight-RGBA high-resolution PNG, resizes in premultiplied-alpha space, clears RGB beneath zero Alpha, and writes straight-RGBA pixels into the addressed cell.

Each unique sequence position maps directly from one approved high-resolution source to one logical target cell. Verification replays the sampler from that source and compares the replayed RGBA pixels with the cell pixel by pixel. This proves direct-render equivalence for the packaged bytes; it makes no claim about how many physical resize operations occurred historically.

A loop may declare an explicit repeated opening cell only when required by the production spec. The closing position reuses the opening cell pixels, points to the opening logical cell, and creates neither another high-resolution source nor another rendering record. Otherwise every sequence position has its own direct source mapping.

## Package closure

One `SpritesheetPackage` contains exactly:

- One untrimmed, unrotated fixed-grid spritesheet PNG
- One authoritative `spritesheet-package/v2` manifest
- Content-addressed canonical-reference and high-resolution-frame PNGs referenced by that manifest

`verify-package` emits a fresh validation report to standard output. It distinguishes machine verification, declared creative relationships, and recorded human reviews; it is not cached inside the package as another authority.

Runtime metadata is derived from the authoritative manifest and cannot define a competing frame order, clip range, duration, event, or anchor. Every production artifact is reachable from the formal lineage. Review evidence and unused candidates remain outside the production graph.

The union of clip positions covers the declared populated cells exactly once, except an explicit repeated opening cell alias. Used cells have exact dimensions and ordering; unused cells have zero Alpha. The sheet dimensions equal `columns * frame_width` by `rows * frame_height`.

## Requests and validation

`prepare-canonical` consumes `canonical-authoring-request/v2`. `build-package` consumes `spritesheet-production-request/v2`. Source, canonical-reference, and high-resolution-frame request paths must be absolute paths to RGBA PNG files; emitted package paths are normalized manifest-relative paths. Use each subcommand's `--help`, emitted diagnostics, and tests for its required current fields.

`verify-package` must check at least:

- Schema version and the closed artifact, review, role, and sampler vocabularies
- Paths, hashes, decoded properties, package closure, and absence of production orphans
- Fixed canonical canvas and target-short-side constraints
- Hash-bound gate subjects and gate ordering
- At least two keyframes and two in-betweens per clip
- Canonical consistency and valid adjacent-keyframe brackets
- Complete cell coverage, layout, clips, durations, events, origin, anchor, and safe bounds
- Pixel-perfect replay of every direct high-resolution-source render
- Opening-cell pixel reuse for every declared explicit loop closure
- Physical package closure with no undeclared files

Exit code `0` means every machine-verifiable package invariant passed. Report human approval and declared creative history separately from machine verification.
