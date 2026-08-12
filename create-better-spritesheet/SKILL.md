---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite sheets for any action."
---

# Create Better Spritesheet

Produce project-faithful animation through an identity-locked source pack, approved key poses, controlled frame derivation, contract-driven assembly, and behavioral quality gates. Treat the target runtime as the final contract.

## 1. Inspect inputs and close gaps

1. Read the user prompt, attachments, linked references, and repository evidence before asking questions. Locate the repository root when applicable, read its agent instructions, and preserve unrelated changes.
2. Inspect design boards, model sheets, existing sprites, animation references, neighboring production assets, asset declarations, clip mappings, event timing, anchors, renderer settings, and visual tests that can answer the contract directly.
3. Separate confirmed facts from missing values. Record the character, action set, directions, camera, loop or one-shot behavior, root-motion policy, frame dimensions, frame count, timing, grid layout, anchor, motion origin, safe bounds, sampling style, and integration scope.
4. Classify the action-reference status as supplied, missing, unavailable, or explicitly declined. When it is missing, actively ask the user to provide one. Accept video, GIF, frame sequences, existing spritesheets, gameplay clips, pose sheets, or a named animation example. Explain that a reference with a similar action, camera, body type, and timing is most useful even when its art style differs.
5. When the user explicitly states that no action reference is needed, record that statement as authorization to design motion from the written intent. Skip the action-reference request and Pinterest search, then present a provisional phase, key-pose, and timing plan for approval before generating frames.
6. When the user says they cannot provide an action reference without declining references, read [reference-search.md](references/reference-search.md) and search Pinterest without asking for separate permission. Filter against the built-in walk-cycle clarity standard, present two to four useful candidates with links and a recommendation, and ask the user to approve one. For walk cycles, inspect the built-in reference and include it as the default candidate.
7. Resolve both master-outline fields from either the user prompt or applicable authoritative repository rules before asking: whether to add an outer silhouette outline, and its width in target-size pixels. Keep every consistently specified field without restating it or asking for confirmation. Ask only for fields that remain missing, ambiguous, or conflicting across sources. Record the width as `none` when the resolved outline decision is disabled.
8. Ask at most three concise, high-impact questions per round. Include only unresolved, ambiguous, or conflicting outline fields in the question set. For the remaining questions, prioritize the action reference; requested action, direction, loop or one-shot behavior, root motion, and gameplay event; then identity reference and technical output contract. Ask only for facts that cannot be reliably discovered from the supplied material or repository.
9. Pause frame generation while a missing answer could materially change identity, motion, timing, direction, layout, or integration. If Pinterest yields no usable reference, report what was searched and ask the user to explicitly authorize motion design from the written intent; then present a provisional phase, key-pose, and timing plan for approval before generating frames.
10. Use disclosed defaults only for low-impact gaps after material questions are resolved. Keep review artifacts in a fresh non-production output directory and production integration outside scope unless requested.

Complete this step only when both outline fields are resolved from the user prompt, applicable authoritative repository rules, or direct user answers, and all other material gaps have user answers, explicit user delegation, or authoritative repository evidence. Read [quality-contract.md](references/quality-contract.md) before generating or reviewing frames. Read [runtime-integration.md](references/runtime-integration.md) only when integration is in scope.

## 2. Lock the identity source pack

Use the approved references as the identity and art-direction source of truth. Preserve the project's anatomy, face, silhouette, hairstyle, outfit, palette, equipment, line treatment, materials, proportions, and identifying details across every action and direction.

Build the smallest source pack that supports the requested motion:

- Keep one canonical neutral frame for identity, scale, and palette.
- Add approved directional views when rotation reveals new shapes or asymmetry.
- Add approved action key poses when articulation, foreshortening, occlusion, or effects cannot be derived faithfully from the neutral frame.
- Separate parts or effect layers when local motion must remain independent.

When suitable transparent sources do not exist, use ImageGen with the approved references to create one source or key pose at a time. Generate a coherent source pack rather than asking a model for a finished multi-frame sheet.

Create every canonical master on a canvas whose shortest side is exactly `512 px`. Preserve the target frame aspect ratio: use `master scale = 512 / min(target frame width, target frame height)`, set the short side to `512`, and round the proportionally scaled long side to the nearest whole pixel. Normalize every source to this fixed canvas and the declared coordinate system.

Apply the resolved master-outline contract during canonical-master generation. When enabled, read [silhouette-outline.md](references/silhouette-outline.md), use the resolved target-size width, derive the color from current references, and add the outline to each fixed-size high-resolution pre-master before any animation deformation, target-size downsample, frame export, or sheet assembly. Treat the unoutlined pre-master as a temporary source; lock the outlined high-resolution result as the canonical master, then derive every production frame from it. Never add, regenerate, thicken, sharpen, or repair the outline on a target-size frame, rendered frame, or assembled sheet; return to the pre-master and rebuild the outlined canonical master instead. When disabled with width `none`, lock the unoutlined result as the canonical master.

Complete this step only when every canonical master has a `512 px` short side and identity, direction, visual scale, palette, equipment handedness, anchor conventions, and outline treatment agree across the source pack.

### Pass the target-size readability gate

Downsample representative canonical masters and the most extreme key pose once to final size. Inspect at native `1×` and measure the occupied Alpha bounds. Evaluate the final master treatment, including its outer silhouette outline when required. If identity or action silhouettes remain muddy despite a correct pipeline, read [optical-sizing.md](references/optical-sizing.md), prepare one bounded optical-size candidate, and obtain static approval before producing all frames.

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

Begin with canonical masters whose outline treatment is already locked. For smooth raster art, deform at high resolution in premultiplied Alpha and downsample each frame once. For pixel art, use the project's discrete palette, pixel clusters, and nearest-neighbor workflow. Treat target-size frames as terminal derivatives rather than outline-processing inputs. Keep all frames on the declared canvas; preserve the animation origin while allowing intentional body or effect travel inside it.

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

Report user-provided references, answered questions, delegated decisions and defaults, generated artifacts, clip-by-clip validation, visual findings, runtime changes and tests, and remaining uncertainty separately. Keep staging, committing, publishing, and production replacement outside scope unless requested.
