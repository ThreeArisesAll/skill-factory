---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any action."
---

# Create Better Spritesheet

Produce runtime-ready animation through one evidence-bound lineage:

`ProductionSpec -> AdmittedCanonicalReferenceSet -> ApprovedHighResolutionSequence -> deterministic target-cell rendering -> SpritesheetPackage`

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

Complete this step when material decisions are authoritative, answered, or explicitly delegated and the package subset can be serialized as `spritesheet-production-request/v3`. Read [quality-contract.md](references/quality-contract.md) before image production. Read [runtime-integration.md](references/runtime-integration.md) only for requested integration.

## 2. Prepare and admit canonical references

Create one neutral identity source for each required camera or direction. Keep action poses out of canonical authoring.

Run `prepare-canonical` with `canonical-authoring-request/v3`. It normalizes the authoring source to the fixed high-resolution canvas and, when enabled, deterministically expands its outer silhouette according to [silhouette-outline.md](references/silhouette-outline.md). Require it to emit `canonical-reference-candidate.png`, `canonical-reference-evidence.json`, `canonical-admission-proof.json`, and content-addressed original authoring-source evidence. Apply [optical-sizing.md](references/optical-sizing.md) before rerunning preparation when native-size readability requires static redesign.

Require machine replay to validate the complete `canonical-reference-evidence/v3` record, content-addressed authoring source, candidate, target geometry, declared algorithms, and resolved outline before accepting `canonical-admission-proof/v1`. Then review identity, direction, visual mass, palette, handedness, anchor conventions, transparency, and outline aesthetics. Bind `canonical-approval` to the exact candidate hash and admission-proof hash.

Treat visual linework as aesthetic evidence only. Require admission replay to prove outline execution. Reuse only an approved canonical whose exact bytes and complete admission evidence match the current request; otherwise rerun canonical preparation and dependent approvals.

Complete this step when every direction has one machine-admitted candidate and a later canonical approval bound to its candidate and proof hashes.

## 3. Approve motion sources

Generate at least two new high-resolution keyframes per clip from the applicable admitted canonical and approved action evidence. Present the complete keyframe set together and record a `keyframe-set-approval` bound to the canonical admission proof and ordered keyframe bytes.

Generate at least two new high-resolution in-betweens per clip from the same admitted canonical and adjacent approved keyframes. Add and reapprove a keyframe when an interval does not constrain the spatial change.

Review the complete sequence for motion, volume, projection, occlusion, identity, timing, contacts, and events. Record a `sequence-approval` bound to the canonical admission proof and every ordered high-resolution-frame hash.

Complete this step when each clip has at least two keyframes and two in-betweens and all hash-bound gates match current bytes.

## 4. Build the package

Run `build-package` with `spritesheet-production-request/v3`. Reference each prepared candidate, authoring evidence file, and admission proof in its canonical input. Require the builder to validate and package those files, replay every canonical admission, and verify approval bindings before accepting canonical bytes. Render each unique approved high-resolution source directly into its logical cell with `lanczos-premultiplied-v1`.

When required, reuse opening-cell pixels at the explicit closing position. Create no additional high-resolution source or render for that alias. Treat logical cells as sheet addresses, not production artifacts.

Complete this step when the fixed-grid sheet and `spritesheet-package/v3` `manifest.json` agree on admission proofs, dimensions, order, clips, timing, events, anchors, unused cells, and loop behavior.

## 5. Verify and hand off

Run `verify-package`. Require it to replay canonical admission and target-cell sampling from packaged evidence and sources. Then inspect frames at native `1x`, loops for at least three cycles, and one-shots through their transition or terminal hold.

Route identity, transparency, optical, or outline defects to canonical authoring; route pose, volume, timing, contact, or transition defects to keyframe or sequence generation; route metadata defects to the production spec and package build. Repeat every invalidated proof and approval.

When integration is requested, follow [runtime-integration.md](references/runtime-integration.md), update repository contracts atomically, and validate the real runtime. Keep staging, committing, publishing, and production replacement outside scope unless requested.

Complete the skill only when schema checks, admission replay, hash-bound gates, sampler replay, cell equality, action checks, native-size review, and requested runtime verification pass. Report machine facts, recorded approvals, supplied evidence, visual findings, changes, tests, and uncertainty separately.
