---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any action."
---

# Create Better Spritesheet

Produce runtime-ready animation through one evidence-bound lineage:

`ProductionSpec -> AdmittedCanonicalReferenceSet -> ApprovedRawHighResolutionSequence -> deterministic batch rendering -> SpritesheetPackage`

Use only:

```bash
<python> <skill-dir>/scripts/spritesheet_pipeline.py prepare-canonical|build-package|verify-package
```

Treat CLI behavior and tests as the executable source of truth for exact fields and layout. Read [lineage-evidence.md](references/lineage-evidence.md) for admission, package, and proof semantics.

## 1. Resolve the production spec

1. Inspect the prompt, attachments, repository rules, asset declarations, sprites, animation mappings, renderer settings, and visual tests.
2. Resolve identity, actions, directions, camera, playback, root motion, dimensions, counts, timing, grid, coordinate contract, events, sampling, outline, and integration scope. Keep planning-only material outside the closed request schema.
3. Follow [motion-design.md](references/motion-design.md) for action evidence and motion planning. Ask at most three material questions per round; pause image production while an answer could change identity, motion, timing, layout, or integration.
4. Execute a consistently resolved outline `enabled` state and `target_width` without reconfirmation. Ask only for missing, ambiguous, or conflicting values.
5. Require a target shortest side below `512 px`, a target longest side at most `4096 px`, and a derived high-resolution longest side at most `16384 px`.

Complete this step when material decisions are authoritative, answered, or explicitly delegated and the package subset can be serialized as `spritesheet-production-request/v4`. Read [quality-contract.md](references/quality-contract.md) before image production. Read [runtime-integration.md](references/runtime-integration.md) only for requested integration.

## 2. Prepare and admit canonical references

Create one neutral identity source for each required camera or direction. Keep action poses out of canonical authoring.

Run `prepare-canonical` with `canonical-authoring-request/v3`. It normalizes the authoring source to the fixed high-resolution canvas and, when enabled, deterministically expands its outer silhouette according to [silhouette-outline.md](references/silhouette-outline.md). Require it to emit `canonical-reference-candidate.png`, `canonical-reference-evidence.json`, `canonical-admission-proof.json`, and content-addressed original authoring-source evidence. Apply [optical-sizing.md](references/optical-sizing.md) before rerunning preparation when native-size readability requires static redesign.

Require machine replay to validate the complete `canonical-reference-evidence/v3` record, content-addressed authoring source, candidate, target geometry, declared algorithms, and resolved outline before accepting `canonical-admission-proof/v1`. Then review identity, direction, visual mass, palette, handedness, anchor conventions, transparency, and outline aesthetics. Bind `canonical-approval` to the exact candidate hash and admission-proof hash.

Treat visual linework as aesthetic evidence only. Require admission replay to prove canonical outline execution. The canonical is an identity, art-direction, camera, and direction reference; neither its pixels nor its formal outline propagate to a newly generated pose. Reuse only an approved canonical whose exact bytes and complete admission evidence match the current request; otherwise rerun canonical preparation and dependent approvals.

Complete this step when every direction has one machine-admitted candidate and a later canonical approval bound to its candidate and proof hashes.

## 3. Approve the complete frame-description plan

Before generating any keyframe source, create one complete, ordered frame-description plan covering every playback position in every clip and direction in the current production batch. Follow the `Complete frame-description gate` in [motion-design.md](references/motion-design.md). Present the entire current plan to the user and explicitly ask them to approve it or request changes. Pause all image generation while approval is unresolved.

If the user changes any entry, invalidate the prior plan approval, incorporate the changes, recompute affected indices, roles, brackets, timing, events, and aliases, then present the entire revised plan again. A partial diff, silence, continued discussion, or approval of only selected frames does not approve the batch. Any later production departure from the approved plan closes this gate again.

Complete this step only when the user explicitly approves the latest complete frame-description plan. Keep this planning review outside `spritesheet-production-request/v4`; do not reopen consistently resolved outline settings during this confirmation.

## 4. Approve raw motion sources

Generate at least two new raw high-resolution keyframe sources per clip from the latest user-approved complete frame-description plan, using the applicable admitted canonical and approved action evidence as creative references. Finish every operation that can change a source's Alpha boundary, including background removal, Alpha cleanup, cropping, normalization, and optical correction, before approval. The resulting Alpha is the authoritative pose silhouette.

Present the complete keyframe set together and record a `keyframe-set-approval` bound to the canonical admission proof and ordered raw source bytes. Review identity, pose, projection, authoritative Alpha, and outline suitability; record canonical use and obedience as declared creative relationships rather than machine facts.

Generate at least two new raw high-resolution in-between sources per clip using the same admitted canonical and adjacent approved keyframes as creative references. Complete every Alpha-changing operation before sequence approval. Add and reapprove a keyframe when an interval does not constrain the spatial change.

Review the complete raw sequence for motion, volume, projection, occlusion, identity, authoritative Alpha, timing, contacts, and events. Record a `sequence-approval` bound to the canonical admission proof and every ordered high-resolution frame source hash. Do not create per-frame admission objects: review gates bind raw bytes, while deterministic frame rendering is proven later by batch replay.

Complete this step when each clip has at least two keyframes and two in-betweens and all hash-bound gates match current bytes.

## 5. Build the package

Run `build-package` with `spritesheet-production-request/v4`. Reference each prepared candidate, authoring evidence file, and admission proof in its canonical input. Require the builder to validate and package those files, replay every canonical admission, and verify approval bindings before accepting canonical bytes.

For each unique approved raw high-resolution source, require one deterministic in-memory frame rendering: treat its final Alpha as authoritative, apply the resolved outward silhouette outline at high resolution or the declared identity operation when disabled, then resize that outlined buffer exactly once with `lanczos-premultiplied-v1` into its target cell. Keep the outlined high-resolution buffer ephemeral. Apply no outline operation to a target cell or assembled sheet.

Require the manifest's top-level `rendering` field to embed one `spritesheet-rendering-receipt/v1` batch receipt. It binds every raw source hash, outlined-buffer and target-cell decoded-RGBA hash, outline contract and algorithm, sampler, resolved high-resolution outline width, and final sheet decoded-RGBA hash. Assembly binds ordered logical uses, cell geometry, and layout. The receipt proves the pixel equation by replay; it is not a claim about whether the generator obeyed the canonical.

When required, reuse opening-cell pixels at the explicit closing position. Create no additional high-resolution source or render for that alias. Treat logical cells as sheet addresses, not production artifacts.

Complete this step when the fixed-grid sheet and `spritesheet-package/v4` `manifest.json` agree on admission proofs, raw source bytes, batch rendering receipt, dimensions, order, clips, timing, events, anchors, unused cells, and loop behavior.

## 6. Verify and hand off

Run `verify-package`. Require it to replay canonical admission and the complete deterministic batch rendering from packaged raw sources, reproducing every target cell and the final spritesheet exactly. Then inspect frames at native `1x`, loops for at least three cycles, and one-shots through their transition or terminal hold.

Route an identity or canonical art-direction defect to canonical authoring. Route an incorrect pose silhouette, transparency, background-removal edge, or raw-source optical defect to raw keyframe or sequence authoring. Route incorrect deterministic ring pixels, clipping, sampling, or assembly to the renderer, outline contract, or package build. Route metadata defects to the production spec and package build. Repeat every invalidated proof, approval, receipt, and package output.

When integration is requested, follow [runtime-integration.md](references/runtime-integration.md), update repository contracts atomically, and validate the real runtime. Keep staging, committing, publishing, and production replacement outside scope unless requested.

Complete the skill only when schema checks, canonical admission replay, hash-bound raw-source gates, batch rendering replay, sheet equality, action checks, native-size review, and requested runtime verification pass. Report machine-verified pixel facts, recorded reviews, declared creative relationships, supplied evidence, visual findings, changes, tests, and uncertainty separately.
