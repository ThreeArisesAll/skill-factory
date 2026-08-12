---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any action."
---

# Create Better Spritesheet

Produce runtime-ready animation through one formal lineage:

`ProductionSpec -> CanonicalReferenceSet -> ApprovedHighResolutionSequence -> deterministic target-cell rendering -> SpritesheetPackage`

The only production entry point is:

```bash
<python> <skill-dir>/scripts/spritesheet_pipeline.py prepare-canonical|build-package|verify-package
```

Use the CLI help and tests as the executable source of truth for request fields and file layout. Use [lineage-evidence.md](references/lineage-evidence.md) for the package contract and evidence boundaries.

## 1. Establish the production spec

1. Read the prompt, attachments, repository instructions, asset declarations, existing sprites, animation mappings, renderer settings, and visual tests before asking questions.
2. Record the character, actions, directions, camera, loop or one-shot behavior, root motion, frame dimensions, frame count, durations, grid layout, anchor, safe bounds, event frames, sampling style, outline contract, and integration scope. Keep character identity evidence, art direction, fallback policy, runtime scale, and integration scope in the working plan when they are not fields of the package request.
3. Resolve the action reference by following [motion-design.md](references/motion-design.md). Ask at most three material questions per round and pause generation while an answer could change identity, motion, timing, layout, or integration.
4. Preserve an outline decision and `target_width` when the prompt or authoritative repository rules already determine both consistently. Ask only when either value is missing, ambiguous, or conflicting.
5. Require each target shortest side to be less than `512 px`, each target longest side to be at most `4096 px`, and the derived high-resolution longest side to be at most `16384 px`.

Complete this step when every material field has an authoritative value, a user answer, or explicit user delegation, and the package-build subset can be serialized as `spritesheet-production-request/v2`. The broader working plan remains review evidence rather than an extension of the closed package schema. Read [quality-contract.md](references/quality-contract.md) before producing images. Read [runtime-integration.md](references/runtime-integration.md) only when integration is requested.

## 2. Author and approve canonical references

Create one fixed-canvas identity reference for each required camera or direction. Each canvas preserves the target aspect ratio, has a `512 px` shortest side, and rounds the proportional long side to the nearest integer. Keep action poses out of this stage.

When the outline contract is enabled, apply [silhouette-outline.md](references/silhouette-outline.md) during canonical authoring. When target-size readability requires static redesign, apply [optical-sizing.md](references/optical-sizing.md) before approval. Source images, candidates, unoutlined buffers, and review contact sheets remain authoring evidence outside the production graph.

Run `prepare-canonical` with a `canonical-authoring-request/v2` request. Review identity, direction, visual mass, palette, equipment handedness, anchor conventions, transparency, and outline treatment. Approval binds the exact image bytes by content hash; those bytes become the immutable `canonical-reference` artifact.

Complete this step when every required direction has an approved, content-addressed canonical reference on the fixed canvas and the set forms the `CanonicalReferenceSet`.

## 3. Design motion and approve keyframes

Follow [motion-design.md](references/motion-design.md). Define phases, contacts, root path, timing, events, transitions, keyframe indices, and in-between indices for every clip.

Generate each keyframe as a new high-resolution RGBA image, using the matching canonical reference for identity and art direction and the approved action reference for motion. Generate at least two keyframes per clip. Present the complete keyframe set side by side and obtain `keyframe-set-approval` bound to the exact content hashes before continuing.

Complete this step when every clip has at least two structurally valid keyframes and its entire keyframe set is approved as one hash-bound gate.

## 4. Generate and approve the high-resolution sequence

For each planned gap, generate a new high-resolution in-between from the same canonical reference and the two adjacent approved keyframes. Generate at least two in-betweens per clip. When the endpoints do not constrain a spatial change, add a keyframe, repeat the keyframe-set gate, and regenerate the affected interval.

Review each complete ordered sequence for motion, volume, perspective, foreshortening, occlusion, identity, timing, contacts, and events. Obtain `sequence-approval` bound to every ordered high-resolution-frame hash.

Complete this step when each clip contains at least two keyframes and two in-betweens, all frames use the single `high-resolution-frame` artifact type with a `keyframe` or `in-between` role, and the ordered sequence has hash-bound approval.

## 5. Build the spritesheet package

Run `build-package` with a `spritesheet-production-request/v2` request. The pipeline directly renders each unique approved high-resolution source into its logical sheet cell with `lanczos-premultiplied-v1`. Smooth-raster resizing operates in premultiplied-alpha space; stored PNG files are straight RGBA.

When a loop contract requires an explicit repeated opening cell, reuse the opening cell pixels at the closing position. This adds no high-resolution artifact and performs no second render. Logical cells are addresses inside the spritesheet, not standalone production artifacts or editable PNG stages.

The sole final deliverable is one `SpritesheetPackage`: the spritesheet, one authoritative `spritesheet-package/v2` manifest, and the content-addressed canonical and high-resolution sources referenced by that manifest. Any runtime metadata view is a projection of the manifest.

Complete this step when the fixed-grid sheet and authoritative manifest agree on dimensions, order, clips, durations, events, anchors, unused cells, and loop behavior.

## 6. Verify and hand off

Run `verify-package` and retain its fresh categorized output as the validation report. Require the verifier to replay `lanczos-premultiplied-v1` from every unique approved high-resolution source and prove pixel by pixel that each populated cell equals its direct render. For an explicit repeated opening cell, require pixel equality with the opening cell. Then inspect every frame at native `1x`, loops for at least three cycles, and one-shots through their transition or terminal hold.

Route corrections by source:

- Canonical identity, transparency, or outline defects return to canonical authoring and invalidate all downstream approvals and package outputs.
- Action, pose, volume, timing, or transition defects return to high-resolution keyframes or sequence generation.
- Native target-cell readability or sampling defects return to the canonical reference or responsible high-resolution source, followed by a package rebuild.

When integration is requested, follow [runtime-integration.md](references/runtime-integration.md), update the repository contracts atomically, and validate the real runtime. Keep staging, committing, publishing, and production replacement outside scope unless requested.

Complete the skill only when schema validation, hash-bound gates, sampler replay, cell equality, action-specific checks, native-size visual review, and any requested runtime verification pass. Report machine-verified facts, human approvals, supplied evidence, visual findings, changes, tests, and remaining uncertainty separately.
