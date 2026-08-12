---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any action."
---

# Create Better Spritesheet

Produce project-faithful animation through one mandatory production lineage: high-resolution pre-master, resolved outline treatment, locked canonical master, multiple generated high-resolution keyframes, multiple generated high-resolution in-betweens, one downsample per approved high-resolution frame, target frames, and contract-driven assembly. Treat the target runtime as the final contract.

## 1. Inspect inputs and close gaps

1. Read the user prompt, attachments, linked references, and repository evidence before asking questions. Locate the repository root when applicable, read its agent instructions, and preserve unrelated changes.
2. Inspect design boards, model sheets, existing sprites, animation references, neighboring production assets, asset declarations, clip mappings, event timing, anchors, renderer settings, and visual tests that can answer the contract directly.
3. Separate confirmed facts from missing values. Record the character, action set, directions, camera, loop or one-shot behavior, root-motion policy, frame dimensions, frame count, timing, grid layout, anchor, motion origin, safe bounds, sampling style, and integration scope.
4. Classify the action-reference status as supplied, missing, unavailable, or explicitly declined. When it is missing, actively ask the user to provide one. Accept video, GIF, frame sequences, existing spritesheets, gameplay clips, pose sheets, or a named animation example. Explain that a reference with a similar action, camera, body type, and timing is most useful even when its art style differs.
5. When the user explicitly states that no action reference is needed, record that statement as authorization to design motion from the written intent. Skip the action-reference request and Pinterest search, then present a provisional phase, keyframe, and timing plan for approval before generating frames.
6. When the user says they cannot provide an action reference without declining references, read [reference-search.md](references/reference-search.md) and search Pinterest without asking for separate permission. Filter against the built-in walk-cycle clarity standard, present two to four useful candidates with links and a recommendation, and ask the user to approve one. For walk cycles, inspect the built-in reference and include it as the default candidate.
7. Resolve both master-outline fields from either the user prompt or applicable authoritative repository rules before asking: whether to add an outer silhouette outline, and its width in target-size pixels. Keep every consistently specified field without restating it or asking for confirmation. Ask only for fields that remain missing, ambiguous, or conflicting across sources. Record the width as `none` when the resolved outline decision is disabled.
8. Ask at most three concise, high-impact questions per round. Include only unresolved, ambiguous, or conflicting outline fields in the question set. For the remaining questions, prioritize the action reference; requested action, direction, loop or one-shot behavior, root motion, and gameplay event; then identity reference and technical output contract. Ask only for facts that cannot be reliably discovered from the supplied material or repository.
9. Pause frame generation while a missing answer could materially change identity, motion, timing, direction, layout, or integration. If Pinterest yields no usable reference, report what was searched and ask the user to explicitly authorize motion design from the written intent; then present a provisional phase, keyframe, and timing plan for approval before generating frames.
10. Use disclosed defaults only for low-impact gaps after material questions are resolved. Keep review artifacts in a fresh non-production output directory and production integration outside scope unless requested.

Complete this step only when both outline fields are resolved from the user prompt, applicable authoritative repository rules, or direct user answers, and all other material gaps have user answers, explicit user delegation, or authoritative repository evidence. Read [quality-contract.md](references/quality-contract.md) before generating or reviewing frames. Read [runtime-integration.md](references/runtime-integration.md) only when integration is in scope.

## 2. Lock the canonical master

Use the approved references as the identity and art-direction source of truth. Preserve the project's anatomy, face, silhouette, hairstyle, outfit, palette, equipment, line treatment, materials, proportions, and identifying details across every action and direction.

Build the smallest reference pack that can lock the character before animation generation:

- Keep one high-resolution pre-master for each required camera or direction.
- Use model sheets and directional views to resolve shapes and asymmetry that the pre-master must represent.
- Keep action poses out of this stage; generate them only after the canonical master is locked.

When a suitable transparent pre-master does not exist, use ImageGen with the approved identity and art references to create it. Do not ask a model for action frames or a finished multi-frame sheet at this stage.

Create every canonical master on a canvas whose shortest side is exactly `512 px`. Preserve the target frame aspect ratio: use `master scale = 512 / min(target frame width, target frame height)`, set the short side to `512`, and round the proportionally scaled long side to the nearest whole pixel. Normalize every source to this fixed canvas and the declared coordinate system.

Apply the resolved master-outline contract during canonical-master generation. When enabled, read [silhouette-outline.md](references/silhouette-outline.md), use the resolved target-size width, derive the color from current references, and add the outline to each fixed-size high-resolution pre-master. Treat the unoutlined pre-master as a temporary source and lock the outlined high-resolution result as the canonical master. When disabled with width `none`, lock the unoutlined result as the canonical master. Use the canonical master as the final identity and art-treatment reference for every later keyframe generation. Never animate, deform, rig, or split the canonical master into production frames, and never add, regenerate, thicken, sharpen, or repair its outline on generated frames or assembled sheets; return to the pre-master and rebuild the canonical master instead.

Complete this step only when every canonical master has a `512 px` short side and its identity, direction, visual scale, palette, equipment handedness, anchor conventions, and outline treatment are locked for use as final generation references.

## 3. Design the motion

Read [motion-design.md](references/motion-design.md). For each clip:

1. Define the readable action phases and keyframes.
2. Mark contacts, root path, anticipation, action or apex, recovery, holds, impact or gameplay event frames, and transition endpoints that apply.
3. Allocate frames and durations by perceptual importance rather than spacing every pose evenly.
4. Decide whether the clip repeats, returns to another state, holds its terminal frame, or hands off through a transition.
5. Assign multiple high-resolution keyframes and multiple high-resolution in-betweens to explicit frame indices.
6. Check directional handedness, equipment arcs, camera consistency, perspective, depth order, and occlusion changes.

Use the same production method for every clip: generate multiple high-resolution keyframes from the canonical master, then generate multiple high-resolution in-betweens from adjacent approved keyframes. Do not substitute deterministic deformation, part warping, layered rigging, skeletal animation, morphing, or direct target-size drawing for either generation stage.

Complete this step only when every requested clip has an explicit phase, timing, transition, direction, event, keyframe-index, and in-between-index contract.

## 4. Generate high-resolution keyframes

Use the canonical master as the final identity, appearance, and outline reference for every keyframe. Use the approved action reference only for pose, perspective, depth, contacts, and timing. Generate each keyframe as a new high-resolution RGBA image on the canonical canvas; do not obtain it by warping, rotating, scaling, cutting apart, or otherwise deforming the canonical master.

Generate at least two distinct high-resolution keyframes per clip and add every pose needed to cover articulation, foreshortening, volume rotation, newly visible surfaces, occlusion-order changes, effects, and gameplay events. Generate one keyframe at a time. Preserve the fixed canvas, coordinate system, camera, animation origin, art treatment, and canonical identity while allowing projection, visible area, and near-versus-far scale to change correctly with the pose.

Present all high-resolution keyframes for the clip side by side and obtain approval before generating any in-betweens. Reject paper-doll articulation, flattened volume, incorrect joint projection, missing foreshortening, inconsistent perspective, impossible overlaps, and incorrect depth order.

Complete this step only when every planned high-resolution keyframe exists, matches the canonical master as its final visual reference, passes the structural gate in [motion-design.md](references/motion-design.md), and is approved.

## 5. Generate high-resolution in-betweens

Generate each missing frame from its two adjacent approved high-resolution keyframes. Treat those bracketing keyframes as the motion and spatial endpoints; retain the canonical master as the final identity and art-treatment reference. Generate one high-resolution in-between at a time on the same canvas.

Generate multiple high-resolution in-betweens for every clip. Preserve continuous three-dimensional volume, perspective, foreshortening, joint paths, near-versus-far scale, newly visible surfaces, and occlusion order between the bracketing keyframes. When an interval cannot be connected without inventing or changing important spatial information, promote the required intermediate pose to a new high-resolution keyframe, approve it, and regenerate that interval.

Review the complete ordered high-resolution sequence before any resizing. Regenerate a high-resolution keyframe or in-between to correct structural or visual errors; never repair them after downsampling.

Complete this step only when every planned high-resolution in-between exists, every frame is traceable to its bracketing approved keyframes, and the complete high-resolution sequence passes motion, volume, perspective, occlusion, identity, and timing review.

## 6. Downsample and assemble

Finalize Alpha and frame order at high resolution. For smooth raster art, keep premultiplied Alpha; for pixel art, preserve the project's discrete palette and pixel-cluster rules. Downsample each approved high-resolution keyframe and in-between exactly once to the target frame dimensions. The resulting target frames are terminal derivatives: do not redraw, deform, outline, sharpen, resize, or structurally edit them.

Export contract-ordered RGBA frames with zero-padded filenames. Verify each frame's exact dimensions, anchor coordinate, Alpha cleanup, and sampling before assembly.

Create and maintain the lineage manifest described in [lineage-evidence.md](references/lineage-evidence.md). Record content-addressed pre-masters, canonical masters, high-resolution keyframes, high-resolution in-betweens, target frames, sheet, declared relations and downsample operations, approval evidence, clip indices, and assembly order. Review contact sheets and in-memory target-size controls are evidence only and must never appear as production target-frame artifacts.

Assemble rectangular frames into a horizontal, vertical, or grid sheet:

```bash
<python> <skill-dir>/scripts/assemble_spritesheet.py \
  --frames-dir <absolute-ordered-frames-directory> \
  --pattern '<contract-frame-glob>' \
  --output <absolute-spritesheet.png> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --frame-count <contract-frame-count> \
  --columns <contract-column-count> \
  --order <row-major-or-column-major> \
  --clip <action-direction>:<1-based-start>:<count>
```

Repeat `--clip` for every clip in a combined sheet and preserve the emitted metadata as assembly evidence. Add the final sheet and assembly metadata to the lineage manifest. The mandatory lineage ends in an untrimmed, unrotated fixed-grid spritesheet; do not replace it with a trimmed or rotated atlas.

Complete this step only when sheet dimensions, cell order, unused cells, clip ranges, metadata, and the recorded artifact graph match the live contract.

## 7. Validate mechanically and visually

Validate the lineage evidence first:

```bash
<python> <skill-dir>/scripts/validate_lineage.py \
  --lineage <absolute-lineage-manifest.json>
```

Treat `MACHINE-VERIFIED` as machine-checked evidence-package structure and artifact consistency. Treat `DECLARED` and `REVIEWED` as explicit workflow or human-review evidence, not as mechanical proof of otherwise unobservable creative history.

Then run the general grid validator:

```bash
<python> <skill-dir>/scripts/validate_spritesheet.py \
  --sheet <absolute-spritesheet.png> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --frame-count <contract-frame-count> \
  --columns <contract-column-count> \
  --order <row-major-or-column-major>
```

Add contract-specific flags for safe bounds, transparent corners, sampling thresholds, repeated loop endpoints, or contact checks. Use `--closed-loop-range <label>:<1-based-start>:<count>` only for clips whose contract includes a repeated closing target. Even then, generate a distinct high-resolution closing frame and downsample it once; never copy or reuse a terminal target to create the repeated cell.

Then inspect every frame at native `1×`, every loop for at least three cycles, and every one-shot from entry through its transition or terminal hold. Reject identity drift, paper-doll articulation, flattened volume, incorrect foreshortening or perspective, impossible overlaps, depth-order errors, direction swaps, timing ambiguity, broken arcs, missing anticipation or recovery, contact or root-motion errors, unintended cropping, Alpha contamination, sampling artifacts, wrong cell order, and runtime event misalignment.

If target-size readability fails, read [optical-sizing.md](references/optical-sizing.md), revise the high-resolution pre-master, rebuild the canonical master, and repeat the complete keyframe, in-between, and single-downsample lineage. Never repair the target frames directly.

Complete validation only when lineage structure, generic mechanical checks, every action-specific behavioral gate, and native-size visual review pass, with declared and reviewed claims reported separately from machine-verified facts.

## 8. Integrate only within explicit scope

When integration is requested, follow [runtime-integration.md](references/runtime-integration.md), update every asset and animation contract atomically, run the repository's asset validation and visual coverage, and capture the real runtime result.

Report user-provided references, answered questions, delegated decisions and defaults, generated artifacts, machine-verified lineage facts, declared workflow claims, review evidence, clip-by-clip validation, visual findings, runtime changes and tests, and remaining uncertainty separately. Keep staging, committing, publishing, and production replacement outside scope unless requested.
