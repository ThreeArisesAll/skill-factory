# Spritesheet Package Evidence v3

Use the CLI and tests as the executable source of truth for exact closed fields. Use this reference for stable admission, lineage, and proof semantics.

## Formal lineage

Use exactly:

`ProductionSpec -> AdmittedCanonicalReferenceSet -> ApprovedHighResolutionSequence -> deterministic target-cell rendering -> SpritesheetPackage`

Keep the production artifact vocabulary closed:

- `canonical-reference`
- `high-resolution-frame`
- `spritesheet`

Keep the review gate vocabulary closed:

- `canonical-approval`
- `keyframe-set-approval`
- `sequence-approval`

Treat authoring sources, admission proofs, action references, candidates, contact sheets, and review material as evidence rather than production artifacts. Treat normalization as an in-memory operation with no file or graph node. Treat a target cell as a logical sheet region rather than an artifact or editable PNG stage. Keep project notes outside the closed package schema.

## Canonical admission

Run `prepare-canonical` with `canonical-authoring-request/v3`. Require it to write `canonical-reference-candidate.png`, `canonical-reference-evidence.json`, `canonical-admission-proof.json`, and content-addressed original authoring-source evidence in one atomic output. Require `canonical-reference-evidence/v3` to bind the original source, target geometry, declared derivation algorithms, resolved outline contract, candidate, and metrics.

When outline is enabled, normalize the packaged authoring source in memory and deterministically apply the required outward-outline algorithm even when the source already has visible edge linework. When disabled, replay normalization followed by the declared identity derivation. Accept no visual substitute for replay: edge appearance, embedded linework, filenames, declarations, or review cannot prove the transform ran.

Generate `canonical-admission-proof/v1` only after every required evidence field, file hash, decoded property, contract value, and replayed pixel matches. Bind the proof to the canonical reference, target, outline, derivation, original authoring source, and authoring-evidence hash. Use its exact file hash as the admission revision consumed by later review gates. Package the proof, authoring evidence, and original replay source by content address.

Perform machine admission before canonical review. Bind `canonical-approval` to the admitted candidate hash and admission-proof hash. Reuse an already approved canonical without changing its bytes only when its candidate, evidence, proof, source, and current request match completely. Otherwise prepare a new candidate. Treat any admission proof change as invalidating canonical approval and every dependent keyframe-set approval, sequence approval, and package.

## Package manifest

Use `spritesheet-package/v3` as the sole authority. Keep these semantic domains closed:

```text
contract:               dimensions, sampler, outline, origin, anchor, and safe bounds
artifacts:              the three production artifact types
canonical_admissions:   content-addressed admission proof and replay-evidence references
clips:                  runtime behavior and ordered high-resolution-frame IDs
reviews:                hash-bound approvals plus canonical admission-proof bindings
sampling:               target-cell algorithm and replay obligation
assembly:               fixed-grid layout and source-to-cell mappings
```

Resolve input image and authoring-evidence paths as absolute regular-file paths. Store package paths as normalized relative content addresses. Hash exact file bytes with lowercase SHA-256. Use zero-based indices.

Give every artifact a unique ID, type, package-relative path, hash, decoded size, and `RGBA` mode. Give each high-resolution frame exactly one role, `keyframe` or `in-between`, and its canonical-reference ID. Give every in-between its adjacent approved keyframe IDs.

Record direction, camera, playback, root motion, transition, terminal hold, positive duration per logical position, indexed events, animation origin, anchor, and safe bounds in their closed v3 locations.

## Gate binding

Bind reviews to current bytes and admission state:

- Bind `canonical-approval` to one canonical-reference hash and its canonical admission proof hash.
- Bind `keyframe-set-approval` to the canonical reference, its admission proof hash, and the ordered complete keyframe set.
- Bind `sequence-approval` to the same canonical and admission proof plus the ordered complete high-resolution sequence.

Require all canonical gates before any keyframe-set gate and all keyframe-set gates before any sequence gate. Require at least two keyframes and two in-betweens per clip. Invalidate a gate and all dependent results when any bound bytes or admission proof changes.

Treat human review as recorded aesthetic evidence. Verify its structure and subjects mechanically; make no claim that a machine authenticated the reviewer, observed the creative act, or inferred execution history from appearance.

## Deterministic target rendering

Use `lanczos-premultiplied-v1`. Decode straight RGBA, resize in premultiplied-Alpha space, clear RGB beneath zero Alpha, and write straight RGBA into the addressed cell.

Map each unique sequence position directly from one approved high-resolution source. Replay that source and compare its target cell pixel by pixel. For an explicit repeated opening position, reuse the opening cell pixels and create no extra high-resolution source or render record.

## Package closure

Package exactly one fixed-grid spritesheet, one authoritative v3 `manifest.json`, the referenced content-addressed production PNGs, and the content-addressed admission proofs, authoring evidence, and original authoring sources required for replay. Keep runtime metadata as a projection of `manifest.json`.

Require every production artifact to be reachable, every declared package file to be present, and every package file to be declared. Cover populated cells exactly once except an explicit closing alias. Require unused cells to have zero Alpha and sheet dimensions to equal grid dimensions multiplied by cell dimensions.

## Build and verification

Run `build-package` with `spritesheet-production-request/v3`. Require every canonical input to reference the prepared candidate, `canonical-reference-evidence.json`, and `canonical-admission-proof.json`. Validate the supplied proof bytes against a fresh replay, require every review's admission hash to match that proof, and package the candidate, proof, evidence, and original source by content address.

Run `verify-package` on `spritesheet-package/v3`. Replay admission only from packaged proof and evidence, then replay every target cell. Verify at least:

- Closed schemas, vocabularies, paths, hashes, decoded properties, and physical package closure
- Fixed canonical geometry and target-size bounds
- Authoring-source, candidate, contract, algorithm, and admission-proof consistency
- Exact normalization plus outline or identity replay for every canonical reference
- Admission-bound review subjects, hashes, and ordering
- Canonical consistency, frame roles, and adjacent-keyframe brackets
- Clip runtime metadata, grid layout, complete cell coverage, and unused-cell transparency
- Pixel-perfect target-cell replay and explicit opening-cell reuse

Exit with `0` only when every machine-verifiable invariant passes. Report declared creative relationships and recorded human reviews separately from machine verification.
