# Spritesheet Package Evidence v4

Use the CLI and tests as the executable source of truth for exact closed fields. Use this reference as the sole documentation authority for the complete pixel equation, admission, package, rendering, and replay semantics.

## Formal lineage

Use exactly:

`ProductionSpec -> AdmittedCanonicalReferenceSet -> ApprovedRawHighResolutionSequence -> deterministic batch rendering -> SpritesheetPackage`

Keep the production vocabulary closed:

- `canonical-reference`
- `high-resolution-frame-source`
- `spritesheet`

Keep the review gate vocabulary closed:

- `canonical-approval`
- `keyframe-set-approval`
- `sequence-approval`

Treat canonical authoring sources and admission material, action references, motion-blueprint and spacing-plan decisions, image-generation outputs before final Alpha cleanup, contact sheets, and review presentation material as evidence rather than pixel-package artifacts. Bind applicable job evidence through [production-delivery.md](production-delivery.md). Treat canonical normalization and outlined high-resolution frame buffers as ephemeral in-memory operations. Treat a target cell as a logical sheet region rather than an artifact or editable PNG stage. Keep project notes outside the closed package schema.

## Canonical admission

Canonical authoring remains `canonical-authoring-request/v3`, `canonical-reference-evidence/v3`, and `canonical-admission-proof/v1`. Advance the production job through canonical preparation and require it to write `canonical-reference-candidate.png`, `canonical-reference-evidence.json`, `canonical-admission-proof.json`, and content-addressed original authoring-source evidence in one atomic output. Its internal compatibility adapter may call `prepare-canonical`; invoke that command directly only for scoped pixel-contract work.

When outline is enabled, normalize the packaged canonical authoring source in memory and deterministically apply the required outward-outline algorithm even when the source already has visible edge linework. When disabled, replay normalization followed by the declared identity derivation. Generate the proof only after every required evidence field, file hash, decoded property, contract value, and replayed pixel matches.

Perform machine admission before canonical review. Bind `canonical-approval` to the admitted candidate hash and admission-proof hash. Reuse an approved canonical only when its exact candidate, evidence, proof, source, and current request match completely.

The admitted canonical is an identity, art-direction, camera, and direction reference for generating poses. Its outline proof applies only to its own candidate pixels. Record whether generation used or obeyed the canonical as declared creative lineage; never infer that a new pose inherited canonical pixels or its formal silhouette ring.

## Authoritative raw sources

A high-resolution frame source becomes eligible for review only after every operation that can change its Alpha boundary has completed. This includes background removal, Alpha cleanup, crop placement, canvas normalization, and optical correction. Its resulting Alpha is the authoritative pose silhouette consumed by deterministic rendering.

Give every v4 request frame a unique ID, role (`keyframe` or `in-between`), and absolute regular-file `source_path`. Give every packaged raw source a package-relative content-addressed path, lowercase SHA-256, decoded size, `RGBA` mode, and canonical-reference ID. Give every in-between its adjacent approved keyframe IDs. Only an explicit loop-closing alias may reuse its clip's opening raw source and rendered cell.

No per-frame admission object is required. Review gates bind the exact raw source bytes; the batch rendering receipt and replay prove the later pixel derivation.

## Gate binding

Bind reviews to current raw bytes and canonical admission state:

- Bind `canonical-approval` to one canonical-reference hash and its canonical admission-proof hash.
- Bind `keyframe-set-approval` to the canonical reference, its admission-proof hash, and the ordered complete raw keyframe-source hashes.
- Bind `sequence-approval` to the same canonical and admission proof plus the ordered complete raw high-resolution frame source hashes.

Require all canonical gates before a keyframe-set gate and all keyframe-set gates before a sequence gate. Derive the necessary keyframes and in-betweens from the approved action topology in [motion-design.md](motion-design.md). Any bound byte or proof change invalidates its gate and every dependent result under [approval-protocol.md](approval-protocol.md).

Classify conclusions precisely:

- `REVIEWED`: identity, motion, projection, authoritative mask quality, outline suitability, and aesthetics judged from the bound bytes
- `DECLARED`: the generator used or obeyed the canonical and action evidence
- `MACHINE-VERIFIED`: schemas, hashes, bindings, geometry, deterministic pixel derivation, assembly, and package closure reproduced by code
- `SUPPLIED`: externally produced runtime or provenance evidence whose schema and bindings may be checked without claiming direct observation

Review structure and bound subjects mechanically. Make no claim that a machine authenticated the reviewer, observed a creative act, or inferred generation history from appearance.

Before keyframe generation, require the workflow-level motion-blueprint approval defined in [motion-design.md](motion-design.md). After keyframe-set approval and before in-between generation, require the workflow-level spacing-plan approval. These decisions remain delivery evidence outside the closed v4 package; `canonical-approval`, `keyframe-set-approval`, and `sequence-approval` remain the package review-gate values.

## Deterministic batch rendering

Use one closed rendering equation for each unique approved raw source:

```text
authoritative mask = final Alpha of raw high-resolution frame source
outlined high-resolution buffer = outline(raw source, authoritative mask, resolved outline)
target cell = lanczos-premultiplied-v1(outlined high-resolution buffer, target geometry)
spritesheet = fixed-grid assembly(target cells, layout)
```

When outline is disabled, replace the outline step with its declared identity operation. Apply the outline or identity operation in memory, then resize exactly once in premultiplied-Alpha space. Clear RGB beneath zero Alpha and write straight RGBA into the addressed cell. Never apply a silhouette outline to a target cell or assembled sheet.

For an explicit repeated opening position, reuse the opening target-cell pixels and create no additional raw source or render. Logical cells remain sheet addresses.

Embed one `spritesheet-rendering-receipt/v1` object in the manifest's top-level `rendering` field. Bind the exact raw source hashes, authoritative-Alpha policy, outline or identity algorithm, resolved high-resolution outline width, sampler, each ephemeral outlined-buffer decoded-RGBA hash, each target-cell decoded-RGBA hash, and the final sheet decoded-RGBA hash. Bind ordered logical uses, cell geometry, layout, and aliases in `assembly`. The outlined high-resolution buffers remain ephemeral.

## Package manifest and closure

Use `spritesheet-package/v4` as the sole pixel-package authority. Keep these semantic domains closed:

```text
contract:          dimensions, outline, origin, anchor, and safe bounds
sources:           canonical references and raw high-resolution frame sources
canonical state:   admission proofs, replay evidence, and canonical approvals
clips:             runtime behavior and ordered raw-source IDs
reviews:           hash-bound keyframe and sequence reviews
rendering:         spritesheet-rendering-receipt/v1 batch inputs, algorithms, and decoded-RGBA hashes
assembly:          fixed-grid source-to-cell mappings and explicit aliases
```

Resolve input files as absolute regular-file paths. Store package paths as normalized relative content addresses. Package exactly one fixed-grid spritesheet, one authoritative v4 `manifest.json`, referenced content-addressed source PNGs, and canonical admission material required for replay. Treat manifest schema and internal bindings as `MACHINE-VERIFIED`; treat clip, timing, anchor, event, and transition meaning as `DECLARED` or `REVIEWED`. Keep an external runtime projection separate from manifest metadata under [production-delivery.md](production-delivery.md). Wrap job, review, diagnostic, and runtime evidence around the unchanged pixel package through that delivery envelope.

Require every packaged source to be reachable, every declared file to be present, and every package file to be declared. Cover populated cells exactly once except an explicit closing alias. Require unused cells to have zero Alpha and sheet dimensions to equal grid dimensions multiplied by cell dimensions.

## Build and verification

Use `spritesheet_production.py advance` as the primary production seam. Its internal compatibility adapter runs `build-package` with `spritesheet-production-request/v4`. Use `spritesheet_pipeline.py build-package` directly only for scoped pixel-contract work. Require every canonical input to reference the prepared v3 candidate and evidence plus its v1 admission proof. Require every motion frame to provide the `source_path` of an approved raw high-resolution frame source. Replay canonical admission, validate review bindings, render every unique source in memory, assemble the sheet, and emit the v4 manifest with its top-level `spritesheet-rendering-receipt/v1` rendering object.

Use `spritesheet_production.py verify` for normal read-only verification. Use the compatibility `spritesheet_pipeline.py verify-package` command directly only for scoped pixel-contract work. Replay canonical admission from packaged evidence, then replay the entire deterministic batch rendering from packaged raw sources and compare the final sheet pixel for pixel. Verify at least:

- Closed schemas, vocabularies, paths, hashes, decoded properties, and package closure
- Canonical authoring-source, candidate, contract, algorithm, and admission-proof consistency
- Raw-source identity, role, canonical association, dimensions, mode, and authoritative Alpha
- Admission-bound review subjects, hashes, ordering, and adjacent-keyframe brackets
- Outline or identity rendering for every unique raw source before a single target resize
- Clip metadata, grid layout, complete cell coverage, transparent unused cells, and explicit aliases
- Receipt completeness and exact final spritesheet replay

Exit with `0` only when every machine-verifiable invariant passes. Report recorded reviews, declared creative relationships, and machine-verified facts separately.
