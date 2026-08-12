---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any project, action, and direction. Use for idle, locomotion, attacks, jumps, casting, interactions, hurt or death clips; loops and one-shots; directional sets; rectangular frames and grid layouts; identity consistency, timing, target-size readability, alpha or sampling artifacts, assembly, validation, and runtime integration."
---

# Create Better Spritesheet

Produce project-faithful animation through an identity-locked source pack, approved key poses, controlled frame derivation, contract-driven assembly, and behavioral quality gates. Treat the target runtime as the final contract.

## 1. Establish the live contract

1. Locate the repository root when a repository is in scope. Read its agent instructions and the user-named art, asset, animation, and runtime references completely.
2. Inspect `git status --short`; preserve unrelated and pre-existing changes.
3. Visually inspect the user-named design board, model sheet, existing sprite, animation reference, or neighboring production asset. If none is named, locate likely sources and state which ones will be authoritative.
4. Read the live asset declaration, clip and state mappings, event timing, frame order, scale, anchor or pivot, renderer options, and relevant visual tests before claiming compatibility.
5. Record the character, action set, directions, camera, loop or one-shot behavior, root-motion policy, frame width and height, frame count per clip, per-frame timing, grid layout and order, anchor, baseline or motion origin, safe bounds, sampling style, and integration scope.
6. Label missing material values as assumptions. Keep review artifacts in a fresh non-production output directory and production integration outside scope unless requested.

Complete this step only when every contract field is explicit or marked as an assumption. Read [quality-contract.md](references/quality-contract.md) before generating or reviewing frames. Read [runtime-integration.md](references/runtime-integration.md) only when integration is in scope.

## 2. Lock the identity source pack

Use the approved references as the identity and art-direction source of truth. Preserve the project's anatomy, face, silhouette, hairstyle, outfit, palette, equipment, line treatment, materials, proportions, and identifying details across every action and direction.

Build the smallest source pack that supports the requested motion:

- Keep one canonical neutral frame for identity, scale, and palette.
- Add approved directional views when rotation reveals new shapes or asymmetry.
- Add approved action key poses when articulation, foreshortening, occlusion, or effects cannot be derived faithfully from the neutral frame.
- Separate parts or effect layers when local motion must remain independent.

When suitable transparent sources do not exist, use ImageGen with the approved references to create one source or key pose at a time at least four times the target dimensions. Generate a coherent source pack rather than asking a model for a finished multi-frame sheet. Normalize every source to the declared canvas and coordinate system.

Complete this step only when identity, direction, visual scale, palette, equipment handedness, and anchor conventions agree across the source pack.

### Pass the target-size readability gate

Downsample representative sources and the most extreme key pose once to final size. Inspect at native `1×` and measure the occupied Alpha bounds. If identity or action silhouettes remain muddy despite a correct pipeline, read [optical-sizing.md](references/optical-sizing.md), prepare one bounded optical-size candidate, and obtain static approval before producing all frames.

### Apply an optional silhouette outline

Apply an outline only when the live art direction calls for one. Read [silhouette-outline.md](references/silhouette-outline.md), select width and color from current references, and apply the same contract to every approved source before frame production.

## 3. Design the motion

Read [motion-design.md](references/motion-design.md). For each clip:

1. Define the readable action phases and key poses.
2. Mark contacts, root path, anticipation, action or apex, recovery, holds, impact or gameplay event frames, and transition endpoints that apply.
3. Allocate frames and durations by perceptual importance rather than spacing every pose evenly.
4. Decide whether the clip repeats, returns to another state, holds its terminal frame, or hands off through a transition.
5. Check directional handedness, equipment arcs, camera consistency, and mirroring safety.

Choose the production method per clip: deterministic deformation for small secondary motion, layered rigging for reusable articulation, approved key-pose redraw plus controlled in-betweens for large motion, or the project's existing skeletal or authoring pipeline when available.

Complete this step only when every requested clip has an explicit phase, timing, transition, direction, and event contract.

## 4. Produce frames

For smooth raster art, work at high resolution in premultiplied Alpha and downsample each frame once. For pixel art, use the project's discrete palette, pixel clusters, and nearest-neighbor workflow. Keep all frames on the declared canvas; preserve the animation origin while allowing intentional body or effect travel inside it.

Derive related frames from approved sources, layers, rigs, or adjacent key poses. Review identity at each key pose before filling in-betweens. Keep effects on separate layers until timing, color, and bounds are approved.

For the optional planted front-facing breathing recipe, read [procedural-idle.md](references/procedural-idle.md) and use `scripts/build_idle_spritesheet.py`. Treat it as one specialized branch, not the default motion model.

Complete each clip only when its key poses, in-betweens, event frame, transition behavior, and target-size silhouettes satisfy the action contract.

## 5. Normalize and assemble

Export contract-ordered RGBA frames with zero-padded filenames. Verify each frame's exact dimensions, anchor coordinate, Alpha cleanup, and sampling before assembly.

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

Repeat `--clip` for every clip in a combined sheet and preserve the emitted metadata as assembly evidence. For atlases with trimming, rotation, or per-frame pivots, use the project's atlas packer and validate its metadata rather than forcing a fixed grid.

Complete this step only when sheet dimensions, cell order, unused cells, clip ranges, and metadata match the live contract.

## 6. Validate mechanically and visually

Run the general grid validator:

```bash
<python> <skill-dir>/scripts/validate_spritesheet.py \
  --sheet <absolute-spritesheet.png> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --frame-count <contract-frame-count> \
  --columns <contract-column-count> \
  --order <row-major-or-column-major>
```

Add contract-specific flags for safe bounds, transparent corners, sampling thresholds, repeated loop endpoints, or planted contact checks. Use `--closed-loop-range <label>:<1-based-start>:<count>` only for clips whose contract includes a repeated closing frame. Use `--profile idle-planted` only for the procedural idle branch.

Then inspect every frame at native `1×`, every loop for at least three cycles, and every one-shot from entry through its transition or terminal hold. Reject identity drift, direction swaps, timing ambiguity, broken arcs, missing anticipation or recovery, contact or root-motion errors, unintended cropping, Alpha contamination, sampling artifacts, wrong cell order, and runtime event misalignment.

Complete validation only when generic mechanical checks, every action-specific behavioral gate, and native-size visual review pass.

## 7. Integrate only within explicit scope

When integration is requested, follow [runtime-integration.md](references/runtime-integration.md), update every asset and animation contract atomically, run the repository's asset validation and visual coverage, and capture the real runtime result.

Report generated artifacts, contract values and assumptions, clip-by-clip validation, visual findings, runtime changes and tests, and remaining uncertainty separately. Keep staging, committing, publishing, and production replacement outside scope unless requested.
