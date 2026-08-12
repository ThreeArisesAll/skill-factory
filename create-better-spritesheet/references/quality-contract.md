# Spritesheet Quality Contract

## Table of contents

- Live contract
- Identity and art lock
- Identity source pack
- Canonical master contract
- Target pixel budget
- Time, space, and events
- Directional consistency
- Sampling and transparency
- Assembly and metadata
- Acceptance gates
- Failure modes and correction paths

## Live contract

Read the following fields from user material and the current repository. Actively ask for missing values that could change the result. Record a value as an assumption only after the user explicitly delegates the decision:

- Character, action, direction, camera, and state transitions
- User references, Pinterest candidates, selected source, and applicable scope
- Loop, one-shot, terminal hold, or fallback behavior
- Root motion, animation origin, anchor, baseline, and event hotspots
- Frame width and height, frame count per clip, per-frame durations, sheet layout, and order
- Working scale and canonical master width and height
- Safe bounds, runtime scale, and visual mass of neighboring assets
- Line treatment, value range, materials, silhouette, palette, and sampling method
- Authorization boundary between review artifacts and production integration

Every later mechanical metric must be traceable to these fields.

## Identity and art lock

Treat user-approved design boards, model sheets, existing assets, or other references as identity truth. Treat the current project's art rules and neighboring production assets as art-direction truth. Verify:

- Face shape, features, body proportions, and baseline expression
- Hairstyle silhouette, lock count, and endpoints
- Major clothing shapes, footwear, weapons, backpacks, and carried items
- Asymmetric details, equipment hand, markings, and directional elements
- Outer contour, internal structure lines, value hierarchy, materials, and detail density

Keep every direction and extreme action recognizably the same character. Protect silhouette, proportions, palette, and recognition anchors before allocating microdetail.

## Identity source pack

Use one neutral master to lock identity, proportions, and palette. Add directional views, key poses, part layers, and effect layers as required. Small secondary motion may use deterministic deformation from one master. Large joint travel, occlusion changes, perspective compression, or direction changes require independently approved key poses.

Every key pose must share:

- The same identity and art language
- The same target canvas and coordinate semantics
- Compatible visual mass, line width, and palette
- Correct direction, equipment hand, and occlusion order

Approve key poses before producing in-betweens.

## Canonical master contract

Create every canonical master with its shortest side fixed at exactly `512 px`. Scale the long side proportionally from the target frame aspect ratio and round it to the nearest whole pixel. Record the target dimensions, derived master scale, and resulting master dimensions as one traceable contract. Use the exact fixed-canvas rule in `SKILL.md` when a bundled script produces or consumes the master.

Resolve the outer-outline requirement before master generation. When the art direction requires an outline, derive its target-size width and color from current references and generate it within the master-creation step. The outlined output is the canonical master; the unoutlined high-resolution input remains a temporary source. Produce every animation frame and key-pose derivative from a canonical master with the same locked outline treatment.

## Target pixel budget

Use the target-size frame's Alpha bounds to calculate the pixels actually occupied by the character. Define clarity by identity and action-silhouette recognition at native `1×`, not by sharpening strength or edge contrast in an enlarged preview.

For every action, preserve major shapes, force direction, limb relationships, equipment arcs, and event frames first. Make internal texture, flyaway hair, folds, and hardware yield to the remaining pixel budget. If a correctly downsampled key pose remains unreadable, apply target-size optical correction before continuing.

## Time, space, and events

Inspect three continuous contracts frame by frame:

- **Time**: Frame spacing and holds emphasize anticipation, main action, impact, recovery, or terminal state.
- **Space**: Center of mass, root, contacts, motion arcs, and camera direction remain continuous.
- **Events**: Hit, release, landing, interaction completion, and state changes land on the correct visual frames.

For loops, verify the transition from last frame to first. For one-shots, verify entry, event frame, recovery or terminal state, and the following transition. Use a repeated closing frame only when required by the contract.

## Directional consistency

Multi-direction clips share phases, rhythm, visual mass, and event semantics. Validate near and far limbs, occlusion, equipment hand, emblems, hair part, and lighting separately. Approve mirrored reuse only when asymmetric details and gameplay hotspots are safe.

## Sampling and transparency

For smooth raster art, use premultiplied Alpha, high-resolution production, and one final downsample. For pixel art, use a discrete palette, pixel clusters, nearest-neighbor sampling, and integer alignment. Establish the project art treatment before selecting tools and validation thresholds.

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
- Alignment between image order and per-frame durations, events, pivots, or atlas metadata

When a fixed grid cannot express trimming, rotation, or per-frame pivots, use the project's atlas pipeline and validate its metadata.

## Acceptance gates

Mechanical checks cover at minimum:

- Image mode, dimensions, frame count, layout, order, and Alpha integrity
- Canonical master scale, exact `512 px` short side, and outline timing
- Declared loop closures, blank frames, safe bounds, and sampling thresholds
- Action-specific contacts, root behavior, displacement, and event frames

Visual checks cover at minimum:

- Identity, action, and direction are readable at native `1×`.
- Identity is stable across all key poses and in-betweens connect naturally.
- A loop runs three consecutive times without a jump; a one-shot completes its transition or terminal state.
- No incorrect mirroring, equipment-hand swap, broken arc, contact slide, or event misalignment is present.
- No unintended cropping, residual edge color, halo, or sampling artifact is present.
- Visual mass, anchor, filtering, and gameplay feedback are correct in the real runtime.

## Failure modes and correction paths

| Symptom | Root cause | Return to |
| --- | --- | --- |
| Extreme action no longer resembles the character | Frames were generated independently without approved key poses | Identity source pack; lock the key poses first |
| Action intent is unclear | Anticipation, main action, or terminal information is missing | Motion design; rebuild the phases and silhouettes |
| Animation floats | Root, center of mass, contacts, or canvas alignment is inconsistent | Spatial contract; unify coordinate semantics |
| Attack lacks force or events are misaligned | Frames are evenly spaced and event frames are unmarked | Time and events; redistribute holds and impact frames |
| Feet slide in locomotion | Cadence, contact position, and root-motion policy conflict | Locomotion contract; reconcile contacts and displacement |
| Equipment changes hands across directions | Incorrect mirroring or missing directional identity sources | Directional consistency; create independent directional key poses |
| Loop jumps | End and start pose, velocity, or path are discontinuous | Loop transition; close the loop according to the contract |
| One-shot freezes at the end | Recovery, transition, or terminal-state rule is missing | Motion design; complete the state exit |
| Edges are jagged or overblurred | Sampling conflicts with the project art treatment | Sampling chain; use the correct smooth-raster or pixel-art path |
| Detail turns muddy | Repeated editing at small size or repeated resizing | High-resolution source; downsample only once at the end |
| Images are correct but playback is wrong | Sheet order, clip range, or metadata disagrees | Assembly; verify runtime declarations cell by cell |
