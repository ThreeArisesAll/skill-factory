# Motion Design Contract v4

Design motion information before allocating image detail.

## Action reference

When the user has supplied no action reference and has not explicitly declined one, ask for video, gameplay capture, GIF, ordered frames, a pose sheet, photography, or a precisely identifiable animation. Prefer evidence with a similar action, camera, body type, projection, and rhythm; its art style may differ.

When the user explicitly declines an action reference, record authorization to design from written intent and present a provisional phase, keyframe, and timing plan for approval before image generation.

When the user cannot supply a reference without declining one, follow [reference-search.md](reference-search.md), screen Pinterest candidates, and recommend two to four. For a walk, include [walk-cycle-reference.png](../assets/walk-cycle-reference.png) as the default structural candidate. If the search finds no usable evidence, request explicit authorization to design from written intent and present the provisional plan.

Extract phases, duration, rhythm, holds, root motion, center of mass, contacts, arcs, camera, direction, depth travel, newly visible surfaces, occlusion, and gameplay events. Use the admitted canonical as identity, art-direction, camera, and direction evidence. Treat generator use and obedience as declared rather than machine-verified relationships.

## Clip plan

Record for every clip:

- State intent, direction, camera, entry, exit, loop, and transition behavior
- Root-motion or in-place policy; anchor, baseline, overflow, and effect bounds
- Phases, center-of-mass path, contacts, arcs, projection, depth, and occlusion
- Total duration, per-position durations, deliberate holds, and gameplay events
- At least two keyframe indices and at least two in-between indices

Allocate positions by perceptual importance. Anticipation explains what is about to happen, the action or extreme explains what happens, and recovery or the terminal pose explains what follows.

## Complete frame-description gate

Run this gate for every clip and direction, regardless of whether motion comes from supplied evidence or written intent. Before generating any keyframe image, create one revision-labeled, complete, ordered table covering every playback position. For each position, record:

- Stable frame ID, zero-based index, and role: `keyframe`, `in-between`, or `closing alias`
- Motion phase, action beat, and narrative or gameplay purpose
- Full-body pose, joint articulation, facing, and equipment or effect state
- Head, ribcage, and pelvis orientation in three-dimensional space
- Projection, foreshortening, depth scale, newly visible surfaces, front-to-back order, and occlusion
- Root and center-of-mass position, baseline, support and contact state, movement arc, and framing overflow
- Spatial change from the previous position and into the next, including speed trend and directional continuity
- Duration or hold, event assignment, and adjacent keyframe IDs for every in-between

List an explicit repeated opening position as `closing alias of <frame-id>`. It has no authored-frame role, new pose, raw source, or independent motion description.

Present the whole table to the user in one review and ask for explicit approval or requested modifications. Pause every image-generation call. When the user changes any entry, invalidate the prior approval, update all affected relationships, publish the entire revised table rather than a diff, and request approval again. Generate the first keyframe only after the latest complete table is explicitly approved. If production later needs to depart from an approved description, revise and reapprove the complete affected clip table before resuming.

Treat the descriptions as `DECLARED` production intent and the user's explicit decision on the complete current table as `REVIEWED`. Structure may be checked mechanically, but neither generation order nor model obedience is machine-proven by the finished images. Keep the plan outside the closed v4 package schema and keep resolved outline settings outside this confirmation.

## Action branches

### Walk and run

Define contact, down, passing, and up phases with left-right order. Declare in-place or root-motion playback. Running normally uses shorter contacts, longer airborne intervals, and stronger torso counter-rotation. Use the bundled walk reference for phase order, center-of-mass rise and fall, arm counter-swing, and loop structure rather than character design.

### Attack, cast, and interaction

Separate anticipation, action, and recovery. Mark hit, release, or interaction completion. Keep weapons, body, and effects on coherent arcs. A smear is a controlled effect, not a replacement for a readable pose.

### Jump, fall, and land

Separate takeoff, rise, apex, fall, and land. Align airborne positions by root or center of mass. Declare displacement. Landing shows compression, contact, and the following transition.

### Hurt, knockdown, and death

Make impact direction and pose silhouette readable before recoil or state change. Synchronize baseline changes with anchors and collision events. Treat death as a one-shot terminal state unless runtime requirements specify a loop.

## Raw-source finalization

Complete every silhouette-changing operation before presenting a motion gate: background removal, Alpha cleanup, crop placement, canvas normalization, and optical correction. The final Alpha of each raw high-resolution frame source is authoritative for later deterministic outline rendering. A review may judge whether that mask is semantically correct; appearance cannot prove how it was created.

## Keyframe-set gate

Present every finalized raw high-resolution keyframe source for one clip and direction side by side. Approve the exact ordered hashes only when:

1. The pose silhouette communicates action and direction.
2. Identity, proportions, equipment, and art treatment match the canonical reference.
3. Ribcage, pelvis, head, and joints form coherent three-dimensional planes.
4. Projection, foreshortening, depth scale, visible surfaces, and occlusion are possible.
5. Center of mass, contacts, arcs, bounds, authoritative Alpha, and event causality agree with the plan.

This gate completes when at least two keyframes exist and `keyframe-set-approval` binds the applicable canonical hash, its `canonical-admission-proof/v1` file hash, and the entire ordered raw keyframe-source set. Require canonical admission and canonical approval before this gate.

## Sequence gate

Generate each raw in-between using the same canonical reference and its two adjacent approved keyframes. Add a keyframe when the endpoints leave a spatial transition underconstrained. Finalize every in-between's authoritative Alpha, then review the full ordered raw sequence for identity, volume, projection, arcs, occlusion, timing, contacts, events, mask correctness, outline suitability, and transition continuity.

This gate completes when at least two in-betweens exist and `sequence-approval` binds the same canonical hash, the same admission-proof hash, and every ordered raw high-resolution frame source hash before deterministic batch rendering.
