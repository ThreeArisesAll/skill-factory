# Motion Design Contract v3

Design motion information before allocating image detail.

## Action reference

When the user has supplied no action reference and has not explicitly declined one, ask for video, gameplay capture, GIF, ordered frames, a pose sheet, photography, or a precisely identifiable animation. Prefer evidence with a similar action, camera, body type, projection, and rhythm; its art style may differ.

When the user explicitly declines an action reference, record authorization to design from written intent and present a provisional phase, keyframe, and timing plan for approval before image generation.

When the user cannot supply a reference without declining one, follow [reference-search.md](reference-search.md), screen Pinterest candidates, and recommend two to four. For a walk, include [walk-cycle-reference.png](../assets/walk-cycle-reference.png) as the default structural candidate. If the search finds no usable evidence, request explicit authorization to design from written intent and present the provisional plan.

Extract phases, duration, rhythm, holds, root motion, center of mass, contacts, arcs, camera, direction, depth travel, newly visible surfaces, occlusion, and gameplay events. The canonical reference remains the identity and art-direction authority.

## Clip plan

Record for every clip:

- State intent, direction, camera, entry, exit, loop, and transition behavior
- Root-motion or in-place policy; anchor, baseline, overflow, and effect bounds
- Phases, center-of-mass path, contacts, arcs, projection, depth, and occlusion
- Total duration, per-position durations, deliberate holds, and gameplay events
- At least two keyframe indices and at least two in-between indices

Allocate positions by perceptual importance. Anticipation explains what is about to happen, the action or extreme explains what happens, and recovery or the terminal pose explains what follows.

## Action branches

### Walk and run

Define contact, down, passing, and up phases with left-right order. Declare in-place or root-motion playback. Running normally uses shorter contacts, longer airborne intervals, and stronger torso counter-rotation. Use the bundled walk reference for phase order, center-of-mass rise and fall, arm counter-swing, and loop structure rather than character design.

### Attack, cast, and interaction

Separate anticipation, action, and recovery. Mark hit, release, or interaction completion. Keep weapons, body, and effects on coherent arcs. A smear is a controlled effect, not a replacement for a readable pose.

### Jump, fall, and land

Separate takeoff, rise, apex, fall, and land. Align airborne positions by root or center of mass. Declare displacement. Landing shows compression, contact, and the following transition.

### Hurt, knockdown, and death

Make impact direction and silhouette readable before recoil or state change. Synchronize baseline changes with anchors and collision events. Treat death as a one-shot terminal state unless runtime requirements specify a loop.

## Keyframe-set gate

Present every high-resolution keyframe for one clip and direction side by side. Approve the exact ordered hashes only when:

1. Silhouette communicates action and direction.
2. Identity, proportions, equipment, and art treatment match the canonical reference.
3. Ribcage, pelvis, head, and joints form coherent three-dimensional planes.
4. Projection, foreshortening, depth scale, visible surfaces, and occlusion are possible.
5. Center of mass, contacts, arcs, bounds, and event causality agree with the plan.

This gate completes when at least two keyframes exist and `keyframe-set-approval` binds the applicable canonical hash, its `canonical-admission-proof/v1` file hash, and the entire ordered keyframe set. Require the canonical admission proof and canonical approval before this gate.

## Sequence gate

Generate each in-between from the same canonical reference and its two adjacent approved keyframes. Add a keyframe when the endpoints leave a spatial transition underconstrained. Review the full ordered sequence for identity, volume, projection, arcs, occlusion, timing, contacts, events, and transition continuity.

This gate completes when at least two in-betweens exist and `sequence-approval` binds the same canonical hash, the same admission-proof hash, and every ordered `high-resolution-frame` hash before target-cell rendering.
