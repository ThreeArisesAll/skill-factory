# Spritesheet Quality Contract v2

## Production spec

Resolve these fields from user material and authoritative repository evidence. Ask only for material values that remain missing, ambiguous, or conflicting; use assumptions only after explicit delegation.

The working production spec is broader than the closed `spritesheet-production-request/v2` package-build schema. Keep identity sources, art direction, fallback policy, runtime scale, event hotspot geometry, review scope, and integration scope as planning and review evidence. Serialize only the dimensions, outline, coordinate contract, clip runtime metadata, approved production inputs, hash-bound reviews, and grid fields accepted by `build-package`.

- Character, actions, directions, camera, and state transitions
- Action-reference status and selected motion evidence
- Loop, one-shot, repeated-opening-cell, terminal-hold, and fallback behavior
- Root motion, animation origin, anchor, baseline, safe bounds, and event hotspots
- Target width and height, frame counts, clip ranges, durations, grid layout, and order
- Runtime scale, neighboring visual mass, palette, materials, line treatment, and sampling style
- Outer silhouette outline enabled state and target-size outward thickness; require a color source only when enabled
- Review-artifact and runtime-integration scope

The target shortest side is strictly less than `512 px`, the target longest side is at most `4096 px`, and the derived high-resolution longest side is at most `16384 px`. Canonical canvases preserve the target aspect ratio with a `512 px` shortest side and a proportionally rounded long side.

When authoritative inputs consistently specify outline enabled state and `target_width`, keep those values without restating or reconfirming them. Ask only for an unresolved or conflicting field. Use `none` for width when outline is disabled.

## Canonical reference gate

The canonical reference is the first formal production image. Author it on the fixed canonical canvas from approved identity and art-direction evidence. Resolve optical design, transparency, and the optional outline before approval. Approval seals the exact same pixels and file hash as an immutable `canonical-reference` artifact; no earlier authoring image enters the production graph.

Verify face, anatomy, silhouette, hairstyle, outfit, palette, equipment, asymmetric details, direction, camera, visual mass, anchor semantics, safe bounds, material treatment, transparency, and outline. Use one canonical reference per required camera or direction, with compatible identity and art language across the set.

The canonical reference guides later generation visually. It is not a pose image, parts source, rig, or source of pixels for deterministic deformation.

## High-resolution frame gates

All action images share the artifact type `high-resolution-frame` and use a `keyframe` or `in-between` role.

Generate each keyframe anew from the matching canonical reference as its identity and art reference. Use the action reference for pose, projection, depth, contacts, and timing. Each clip requires at least two keyframes. The `keyframe-set-approval` gate binds the applicable canonical hash followed by the entire ordered keyframe set and verifies identity, three-dimensional volume, body planes, joint projection, foreshortening, near-versus-far scale, visible surfaces, overlap, depth order, contacts, arcs, and event causality.

After that gate, generate every in-between anew from the same canonical reference plus its two adjacent approved keyframes. Each clip requires at least two in-betweens. Add and approve another keyframe when an interval does not sufficiently constrain articulation, projection, visible surfaces, or occlusion topology.

The production method is new image generation. Warp, rig, morph, layered deformation, two-dimensional deformation, and direct target-size drawing do not satisfy either role. The `sequence-approval` gate binds the same canonical hash followed by the complete ordered high-resolution sequence before rendering.

## Motion, direction, and events

Inspect three continuous contracts:

- **Time:** spacing and holds communicate anticipation, action, impact, recovery, and terminal state.
- **Space:** center of mass, root, contacts, arcs, camera, volume, and occlusion remain coherent.
- **Events:** hit, release, landing, interaction completion, and state changes coincide with the intended visual positions.

For loops, review the final-to-opening transition. When the contract requires an explicit repeated opening cell, the package aliases the already-rendered opening pixels at the closing position. For one-shots, review entry, event, recovery or terminal state, and the following transition.

Generate each direction from its own directional canonical reference and newly generated high-resolution frames. Validate handedness, emblems, hair part, lighting, projection, near and far limbs, and occlusion natively for that direction.

## Sampling and target cells

For smooth raster art, the sole production sampler is `lanczos-premultiplied-v1`. It reads straight-RGBA PNG input, resizes in premultiplied-alpha space, and produces straight-RGBA cell pixels. RGB beneath fully transparent output pixels is zero. Pixel-art requests require an explicit production-spec decision because this v2 sampler contract targets smooth raster art.

Each logical target cell is rendered directly from its unique approved high-resolution source. Target cells exist only within the sheet; they are not formal artifacts, standalone PNGs, or editable stages. An explicit repeated opening cell reuses the opening pixels without another source or render.

Verify transparent corners, edge color, absence of halos or haze, declared safe bounds, intentional overflow, and native-size readability. Use enlarged views only to diagnose pixel competition.

## Package and acceptance

The final deliverable is one `SpritesheetPackage`: a fixed-grid, untrimmed, unrotated RGBA sheet; one authoritative `spritesheet-package/v2` manifest; and the content-addressed sources referenced by that manifest. Runtime views are projections of the manifest. `verify-package` emits a fresh categorized report rather than storing a second authority inside the package.

Machine verification covers artifact hashes and decoded properties, closed vocabularies, gate subjects, sequence topology, complete logical-cell coverage, dimensions, order, unused-cell transparency, metadata consistency, deterministic sampler replay, and pixel equality between each direct render and its cell. It does not prove historical resize count or authenticate human approval.

Visual acceptance covers native-size identity and action readability, volumetric continuity, direction, loop or transition behavior, contacts, events, cropping, transparency, sampling, visual mass, anchor, and real-runtime behavior when integration is in scope.

## Correction routing

| Symptom | Return to | Required consequence |
| --- | --- | --- |
| Identity, palette, transparency, or outline is wrong | Canonical authoring | Approve a new canonical hash and invalidate every dependent frame, gate, and package |
| Pose, perspective, volume, occlusion, timing, contact, or event is wrong | High-resolution keyframes or sequence | Repeat the affected keyframe-set or sequence gate before rebuilding |
| Native target-cell readability or sampling fails | Canonical reference or responsible high-resolution source | Correct the source, repeat dependent approvals, and rebuild the package |
| Cell order, clip range, duration, event, or anchor metadata is wrong | Production spec and package build | Regenerate the authoritative manifest and sheet together |

Corrections terminate at an approved source and then regenerate the package. A sheet cell is never patched.
