# Spritesheet Quality Contract

## Table of contents

- Live contract
- Identity and art lock
- Canonical reference pack
- Canonical master contract
- High-resolution keyframes
- High-resolution in-betweens
- Target pixel budget
- Time, space, and events
- Directional consistency
- Sampling and transparency
- Assembly and metadata
- Lineage evidence
- Acceptance evidence and gates
- Failure modes and correction paths

## Live contract

Read the following fields from user material and the current repository. Actively ask for missing values that could change the result. Record a value as an assumption only after the user explicitly delegates the decision:

- Character, action, direction, camera, and state transitions
- Action-reference status: supplied, missing, unavailable, or explicitly declined
- User references, Pinterest candidates, selected source, and applicable scope
- Loop, one-shot, terminal hold, or fallback behavior
- Root motion, animation origin, anchor, baseline, and event hotspots
- Frame width and height, final sheet frame count, per-clip global ranges and counts, per-frame durations, sheet layout, and order
- Derived master scale and canonical master width and height
- Safe bounds, runtime scale, and visual mass of neighboring assets
- Line treatment, value range, materials, silhouette, palette, and sampling method
- Resolved outer silhouette outline decision and target-size width, using `none` when disabled
- Authorization boundary between review artifacts and production integration

Every later mechanical metric must be traceable to these fields. Keep outline fields already established consistently by either the user prompt or applicable authoritative repository rules without restating them or asking for confirmation. Ask only for missing, ambiguous, or conflicting outline fields; do not substitute defaults or delegated judgment for an unresolved value.

## Identity and art lock

Treat user-approved design boards, model sheets, existing assets, or other references as identity truth. Treat the current project's art rules and neighboring production assets as art-direction truth. Verify:

- Face shape, features, body proportions, and baseline expression
- Hairstyle silhouette, lock count, and endpoints
- Major clothing shapes, footwear, weapons, backpacks, and carried items
- Asymmetric details, equipment hand, markings, and directional elements
- Outer contour, internal structure lines, value hierarchy, materials, and detail density

Keep every direction and extreme action recognizably the same character. Protect silhouette, proportions, palette, and recognition anchors before allocating microdetail.

## Canonical reference pack

Use one high-resolution pre-master per required camera or direction to lock identity, proportions, palette, and art treatment. Use model sheets and directional views as supporting evidence, but keep action poses out of this stage. The canonical master is a final visual reference for later image generation, not a flat puppet, rig, parts source, or production frame.

Every canonical master must share:

- The same identity and art language
- The same fixed high-resolution canonical canvas and coordinate semantics
- Compatible visual mass, line width, and palette
- Correct direction, equipment hand, and occlusion order

Lock the canonical masters before generating any action keyframes.

## Canonical master contract

Create every canonical master with its shortest side fixed at exactly `512 px`. Scale the long side proportionally from the target frame aspect ratio and round it to the nearest whole pixel. Record the target dimensions, derived master scale, and resulting master dimensions as one traceable contract. Use the exact fixed-canvas rule in `SKILL.md` when a bundled script produces or consumes the master.

Resolve the outer silhouette outline requirement before master generation from the user prompt, applicable authoritative repository rules, or a direct user answer. When enabled, use the resolved target-size width, derive the color from current references, and add the outline to the fixed-size high-resolution pre-master. Lock the outlined output as the canonical master and keep the unoutlined pre-master only as a temporary source. When disabled, record the width as `none` and use the unoutlined canonical master.

Use the canonical master as the final identity, appearance, and outline reference for every high-resolution keyframe generation. Do not animate, deform, rig, split, or downsample it into production frames. Do not run the outline workflow on generated keyframes, generated in-betweens, target frames, or assembled sheets. If the canonical appearance or outline is wrong, return to the pre-master, rebuild the canonical master, and restart downstream generation.

## High-resolution keyframes

Generate multiple distinct high-resolution keyframes for every clip, one image at a time, using the canonical master as the final visual reference and the approved action source as the motion reference. Each keyframe must occupy the canonical canvas and preserve its coordinate system, camera, animation origin, identity, palette, materials, and line treatment.

Cover every pose that defines the action or changes three-dimensional information: entry, anticipation, action or apex, event, recovery, exit, body-plane rotation, major articulation, perspective compression, newly visible surfaces, or occlusion-order changes. Do not create keyframes by transforming canonical-master pixels, layered parts, a rig, or target-size artwork.

Approve all high-resolution keyframes before generating any in-betweens. Approval must verify identity, three-dimensional volume, body-plane orientation, joint projection, foreshortening, near-versus-far scale, newly visible surfaces, overlap, depth order, contacts, and event causality.

## High-resolution in-betweens

Generate multiple high-resolution in-betweens for every clip, one image at a time, from the two adjacent approved keyframes that bracket each missing frame. Use those keyframes as the motion and spatial endpoints and retain the canonical master as the final identity and art-treatment reference.

Do not substitute morphing, scripted deformation, part warping, layered rigging, skeletal animation, target-size drawing, or direct canonical-master derivation. When the endpoints do not sufficiently constrain a change in projection, visible surface, articulation, or occlusion topology, add and approve another high-resolution keyframe before regenerating the interval.

Approve the complete ordered high-resolution sequence before any production resize. Every frame must be traceable to either its canonical-master-backed keyframe generation or its two bracketing approved keyframes.

## Target pixel budget

Use the target-size frame's Alpha bounds to calculate the pixels actually occupied by the character. Define clarity by identity and action-silhouette recognition at native `1×`, not by sharpening strength or edge contrast in an enlarged preview.

For every action, preserve major shapes, force direction, limb relationships, equipment arcs, and event frames first. Make internal texture, flyaway hair, folds, and hardware yield to the remaining pixel budget. Downsample only after all high-resolution keyframes and in-betweens are approved. If a target frame remains unreadable, return to the high-resolution pre-master and repeat the canonical-master, keyframe, in-between, and single-downsample lineage.

## Time, space, and events

Inspect three continuous contracts frame by frame:

- **Time**: Frame spacing and holds emphasize anticipation, main action, impact, recovery, or terminal state.
- **Space**: Center of mass, root, contacts, motion arcs, and camera direction remain continuous.
- **Events**: Hit, release, landing, interaction completion, and state changes land on the correct visual frames.

For loops, verify the transition from last frame to first. For one-shots, verify entry, event frame, recovery or terminal state, and the following transition. Use a repeated closing target only when required by the contract; it must still come from its own distinct, independently generated high-resolution frame and its own single downsample, never from copying or reusing a terminal target.

## Directional consistency

Multi-direction clips share phases, rhythm, visual mass, and event semantics. Generate every direction from its own locked directional canonical master; do not mirror canonical masters, keyframes, in-betweens, target frames, or assembled clips. Validate near and far limbs, occlusion, equipment hand, emblems, hair part, projection, and lighting separately.

## Sampling and transparency

For smooth raster art, use premultiplied Alpha throughout high-resolution generation and one final downsample per approved high-resolution frame. For pixel art, preserve the project's discrete palette and pixel-cluster rules while still following the same canonical-master, keyframe, in-between, and single-resize lineage. Establish the project art treatment before selecting validation thresholds.

After the one production resize, treat every target frame as terminal. Do not redraw, deform, outline, sharpen, resize, or structurally edit it before assembly.

Verify every frame:

- The background is transparent and RGB is zero beneath fully transparent pixels.
- Translucent edges match the art treatment and contain no key-color residue or haze.
- Canvas dimensions, animation origin, and safe bounds are consistent.
- Intentional overflow, effect cropping, or blank frames are declared in the contract.

## Assembly and metadata

Use zero-padded filenames in contract order. After assembly, verify:

- Frame dimensions, total frame count, columns, rows, and total sheet dimensions
- Row-major or column-major order
- Start index and length of every action-direction clip
- Transparency of unused cells
- Alignment between image order and per-frame durations, events, the shared anchor, and spritesheet metadata

The mandatory production artifact is an untrimmed, unrotated fixed-grid spritesheet. Record a shared anchor in the live contract rather than replacing the sheet with per-frame trimming, rotation, or pivots.

## Lineage evidence

Follow [lineage-evidence.md](lineage-evidence.md) and keep one content-addressed manifest for the production run. Record the pre-master-to-canonical relationship, the canonical reference used by every keyframe, an ordered artifact relation from the two approved bracketing keyframes to every in-between, the single declared downsample from every approved high-resolution frame to its target frame, global clip indices, loop and repeated-closing-target fields, subject-specific approval stages and declared order, and final assembly order. Keep the production artifact graph closed; review controls, unused candidates, and alternate derivation branches do not belong in it.

The lineage validator checks manifest structure, artifact hashes and image properties, reference integrity, frame-index coverage, bracketing topology, declared downsample cardinality, and fixed-grid sheet pixels. It cannot observe how an image was actually created, authenticate a human approval, prove that a resize happened exactly once, or prove that no later edit occurred. Report those facts as declared or reviewed evidence rather than machine-verified history.

## Acceptance evidence and gates

Machine-verifiable checks cover at minimum:

- Image mode, dimensions, frame count, layout, order, and Alpha integrity
- Artifact IDs, paths, hashes, image properties, and reference integrity
- Closed artifact, relation, review-stage, and transform-type vocabularies with no orphan production artifacts
- Exact fixed high-resolution canvas derived from the target aspect ratio with a `512 px` short side
- At least two distinct recorded and decoded high-resolution keyframes and at least two distinct recorded and decoded high-resolution in-betweens per clip
- Complete global frame-index coverage and valid linear or declared-loop adjacent-keyframe bracketing
- Exactly one recorded high-resolution source and one downsample declaration for every target frame
- Structurally valid declared review and downsample ordering across canonical lock, keyframes, in-betweens, and resize
- Fixed-grid target-frame order and pixel equality with the assembled sheet
- Presence and structure of loop behavior, blank-frame, safe-bound, and sampling-threshold declarations
- Action-specific contacts, root behavior, displacement, and event frames

Workflow evidence and review must cover at minimum:

- The resolved outline treatment was applied only to the high-resolution pre-master before canonical lock
- Each high-resolution keyframe was newly generated with the canonical master as its final visual reference, not derived by transforming canonical pixels or flat parts
- Each high-resolution in-between was newly generated from its two adjacent approved keyframes, not produced by a rig, warp, morph, scripted deformation, or target-size drawing
- All high-resolution keyframes were approved before in-between generation and the complete high-resolution sequence was approved before resizing
- Each target frame was downsampled exactly once and received no later redraw, outline, sharpening, resize, or structural edit
- Review contact sheets and target-size controls remained evidence only and never entered the production artifact graph

Visual checks cover at minimum:

- Identity, action, and direction are readable at native `1×`.
- Identity is stable across all keyframes and in-betweens connect naturally.
- Body volume, body-plane orientation, joint projection, foreshortening, near-versus-far scale, visible surfaces, overlaps, and depth order remain spatially coherent.
- A loop runs three consecutive times without a jump; a one-shot completes its transition or terminal state.
- No mirrored reuse, equipment-hand swap, broken arc, contact slide, or event misalignment is present.
- No unintended cropping, residual edge color, halo, or sampling artifact is present.
- Visual mass, anchor, filtering, and gameplay feedback are correct in the real runtime.

## Failure modes and correction paths

| Symptom                                          | Root cause                                                                                                     | Return to                                                           |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Extreme action no longer resembles the character | Generated frames drifted from the canonical identity reference                                                 | High-resolution keyframes; regenerate from the canonical reference  |
| Character moves like a flat paper puppet         | Canonical-master pixels or flat parts were deformed instead of generating volumetric keyframes and in-betweens | High-resolution keyframes; regenerate from the canonical reference  |
| Perspective or occlusion changes incorrectly     | Bracketing keyframes do not constrain the spatial transition                                                   | High-resolution keyframes; add the missing structural pose          |
| Action intent is unclear                         | Anticipation, main action, or terminal information is missing                                                  | Motion design; rebuild the phases and silhouettes                   |
| Animation floats                                 | Root, center of mass, contacts, or canvas alignment is inconsistent                                            | Spatial contract; unify coordinate semantics                        |
| Attack lacks force or events are misaligned      | Frames are evenly spaced and event frames are unmarked                                                         | Time and events; redistribute holds and impact frames               |
| Feet slide in locomotion                         | Cadence, contact position, and root-motion policy conflict                                                     | Locomotion contract; reconcile contacts and displacement            |
| Equipment changes hands across directions        | Mirrored reuse or missing directional identity sources                                                        | Directional consistency; generate independent directional keyframes |
| Loop jumps                                       | End and start pose, velocity, or path are discontinuous                                                        | Loop transition; close the loop according to the contract           |
| One-shot freezes at the end                      | Recovery, transition, or terminal-state rule is missing                                                        | Motion design; complete the state exit                              |
| Edges are jagged or overblurred                  | Sampling conflicts with the project art treatment                                                              | Sampling chain; use the correct smooth-raster or pixel-art path     |
| Detail turns muddy                               | Repeated editing at small size or repeated resizing                                                            | High-resolution source; downsample only once at the end             |
| Images are correct but playback is wrong         | Sheet order, clip range, or metadata disagrees                                                                 | Assembly; verify runtime declarations cell by cell                  |
