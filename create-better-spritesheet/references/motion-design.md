# Motion Design Contract v4

Design motion information before allocating image detail. Use the [approval protocol](approval-protocol.md) for every gate in this sequence.

## Action evidence

When the user supplies no action reference and has not declined one, ask for video, gameplay capture, GIF, ordered frames, a pose sheet, photography, or a precisely identifiable animation. Prefer evidence with a similar action, camera, body type, projection, and rhythm; art style may differ.

When the user cannot supply evidence, follow [reference-search.md](reference-search.md). When the user declines action evidence, record authorization to design from written intent. In either case, require an approved motion blueprint before image generation.

Extract phases, duration, rhythm, holds, root motion, center of mass, contacts, arcs, camera, direction, depth travel, newly visible surfaces, occlusion, and gameplay events. Use the admitted canonical for identity, art direction, camera, and direction. Treat generator use and obedience as `DECLARED` relationships.

## Action topology

Choose topology from motion behavior rather than a universal frame quota. Combine topologies when an action genuinely contains multiple structures.

| Topology | Required structural anchors | Spacing emphasis |
| --- | --- | --- |
| Cyclic locomotion | Distinct contacts, support transfers, directional extremes, and a provable loop seam | Weight transfer, footfall rhythm, center-of-mass rise and fall |
| Cyclic ambient or mechanical | Opposing extremes and a reversible or explicitly resettable path | Ease profile, pause distribution, seam continuity |
| Anticipation-action-recovery | Preparation, causal action or impact, and recovery or exit | Acceleration into the event and readable aftermath |
| Ballistic or traversal | Launch, trajectory-defining state, apex or direction change, and landing or exit | Root displacement, airtime, contact timing |
| Sustained hold or channel | Entry, stable hold definition, controlled variation when needed, and exit | Hold duration, secondary motion, transition edges |
| Terminal state | Cause, loss of control or transition, and terminal pose | Irreversible state change and terminal hold |

A topology may need two anchors or many. Add a keyframe wherever the existing anchors fail to determine silhouette, spatial path, projection, contact, event causality, or transition behavior. Add an in-between only when it expresses necessary timing or spatial information. Do not satisfy an abstract keyframe or in-between count.

## Motion-blueprint gate

Before generating motion images, present one revision-labeled blueprint for every clip and direction in the current batch. Record:

- Intent, topology, direction, camera, entry, exit, loop, and transition behavior
- Root-motion or in-place policy; anchor, baseline, overflow, and effect bounds
- Named phases, structural anchors, center-of-mass path, contacts, arcs, projection, depth, and occlusion
- Total duration, rhythm, holds, gameplay events, and event causality
- The evidence supporting each structural decision and every deliberately delegated choice

Complete the gate only when the current blueprint has explicit approval under [approval-protocol.md](approval-protocol.md). Keep the blueprint and decision outside the closed v4 production-request and package schemas; bind them as delivery evidence under [production-delivery.md](production-delivery.md).

## Keyframe authoring and gate

Generate the structural keyframes required by the approved topology and blueprint. For every keyframe, define its phase, pose, joint articulation, head-ribcage-pelvis orientation, projection, foreshortening, depth order, occlusion, root, center of mass, contacts, equipment or effect state, framing, duration, and event relationship.

Complete background removal, Alpha cleanup, crop placement, canvas normalization, and optical correction before review. The resulting Alpha is the authoritative pose silhouette.

Present every finalized raw high-resolution keyframe source for one clip and direction together. Approve the exact ordered hashes only when the set:

1. Determines the topology and communicates action and direction.
2. Preserves identity, proportions, equipment, and art treatment from the canonical.
3. Maintains coherent body planes, projection, foreshortening, visible surfaces, and occlusion.
4. Establishes center of mass, contacts, arcs, bounds, authoritative Alpha, and event causality.

Complete the formal `keyframe-set-approval` only when it binds the applicable canonical hash, its `canonical-admission-proof/v1` file hash, and the entire ordered current keyframe-source set. Add a keyframe and repeat the gate when any interval remains underconstrained.

## Spacing-plan gate

After keyframe-set approval, derive one revision-labeled `spacing-plan/v1` from the approved blueprint and keyframes. Cover every playback position and record:

- Stable frame ID, zero-based index, and role: `keyframe`, `in-between`, or `closing alias`
- Adjacent approved keyframe IDs for each in-between
- Spatial change, movement arc, speed trend, easing, contact transition, and directional continuity
- Duration or hold, event assignment, root and center-of-mass position, and framing overflow
- Pose, projection, depth order, occlusion, newly visible surfaces, equipment, and effect state where these change

Represent an explicit repeated opening position as `closing alias of <frame-id>`. It has no new pose, raw source, or render.

Present the entire current plan and complete its approval under [approval-protocol.md](approval-protocol.md) before generating any in-between. Keep the plan and decision outside the closed v4 schemas; bind them as delivery evidence under [production-delivery.md](production-delivery.md).

## Sequence authoring and gate

Generate each planned raw in-between from the same admitted canonical and its adjacent approved keyframes. Finalize every Alpha-changing operation before review. Review the complete ordered raw sequence for topology, identity, volume, projection, arcs, occlusion, spacing, timing, contacts, events, mask correctness, outline suitability, and transition continuity.

Complete `sequence-approval` only when it binds the applicable canonical and admission-proof hashes plus every ordered current raw high-resolution frame-source hash. Build no package while this binding or any upstream approval is invalid.

## Common action interpretation

- For walk and run, establish contact order, support transfer, passing behavior, vertical center-of-mass path, arm counter-swing, and loop closure. Running usually shortens ground contact and increases airborne time and torso counter-rotation.
- For attacks, casts, and interactions, separate preparation, causal action, and recovery; mark hits, releases, and completion. Keep body, equipment, and effects on coherent arcs.
- For jumps, falls, and landings, distinguish launch, rise, apex, fall, and contact as required by the trajectory. Align airborne poses by root or center of mass and declare displacement.
- For hurt, knockdown, and death, make impact direction and state change readable. Synchronize baseline changes with anchors and collision events; use a terminal hold unless runtime behavior requires otherwise.
