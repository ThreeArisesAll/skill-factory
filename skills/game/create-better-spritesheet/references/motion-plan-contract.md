# Motion Plan Contract

`motion-plan/v2` is the complete, approved source of truth for action structure and every logical playback position. It replaces separate blueprint and spacing-plan ceremonies in the current workflow.

## Action evidence and topology

Use supplied motion evidence when available. If none is available, follow [reference-search.md](reference-search.md) or record explicit authority to design from written intent. Evidence supports motion decisions; it does not authorize copying another character's identity or style.

Choose topology from action behavior, not from a universal frame quota:

| Topology | Structural requirements |
| --- | --- |
| Cyclic locomotion | Contacts, support transfers, directional extremes, center-of-mass path, and a legible seam |
| Cyclic ambient or mechanical | Opposing extremes, reversible path or explicit reset, and hold distribution |
| Anticipation-action-recovery | Preparation, causal event or impact, recoil or follow-through, and recovery or exit |
| Ballistic or traversal | Launch, trajectory, apex or direction change, landing, and root displacement |
| Sustained hold or channel | Entry, stable hold, controlled overlap or variation, and exit |
| Terminal state | Cause, loss of control or transition, terminal pose, and hold policy |

Use as many positions as the action needs and no more. A one-source hold is valid. A repeated hold or loop closure is an alias, not a fabricated image difference.

## Complete plan subject

For every clip record its canonical view, direction, camera, topology, intent, entry, exit, loop behavior, root-motion policy, transition, terminal-hold policy, and action evidence. For every ordered position record:

- Stable ID, role, index, duration, events, phase, action beat, and purpose
- Full-body pose and readable silhouette intent
- Head, ribcage, pelvis, limb, and equipment orientation
- Projection, foreshortening, depth order, occlusion, and newly visible surfaces
- Root, center of mass, contacts, support state, and ground relationship
- Motion arc, spacing, acceleration or deceleration, and transition on each side
- Equipment and effect state

Present the complete current plan for every clip and direction in the batch. Obtain explicit approval before accepting or producing any motion image. A partial excerpt, a diff, or approval of selected frames does not complete the gate.

## Position roles

- `keyframe`: a concrete high-resolution source that determines action structure, contact, event causality, spatial path, or a major silhouette change.
- `in-between`: a concrete high-resolution source that expresses required spacing, arc, overlap, contact transition, projection change, or timing information between structural keys.
- `alias`: a logical playback position that reuses an earlier concrete source in the same clip. Use `hold` for timing reuse and `closing` for the final seam of a loop.

An alias has its own ID, duration, events, purpose, and transitions, but no source path, raster artifact, or rendering-receipt frame. A closing alias must be the last position of a loop.

## Animation review standards

Evaluate the ordered sources and final playback for:

- Anticipation, causal action, settle, recovery, follow-through, and overlapping secondary motion
- Weight, inertia, momentum, acceleration, deceleration, and coherent motion arcs
- Root trajectory, center-of-mass support, planted contacts, foot sliding, landing compression, and release timing
- Distinct key poses, intentional breakdowns, justified holds, event positions, and readable loop closure
- Volume, projection, screen direction, action intent, and equipment side across directional variants

Machine checks may prove order, durations, events, aliases, source hashes, cell placement, Alpha measurements, and configured centroid limits. They cannot prove weight, appeal, anatomy, contact intent, or performance timing; those remain explicit visual-review subjects.

## Invalidation and recovery

Any material change to a clip or position invalidates the approved motion plan and every motion image, review, package, diagnostic, and delivery descendant. Preserve unchanged canonical approval when its identity inputs remain exact. Rebuild the full current plan, present it again, and obtain new approval before resuming image work.

When a generated result deviates from the approved plan, stop. Either reject and regenerate the source under the same plan, or revise the plan, present the complete revised version, reapprove it, and restart affected image work. Never silently adopt a visual deviation after approval.
