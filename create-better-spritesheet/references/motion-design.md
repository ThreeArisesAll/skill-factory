# Motion Design Contract

Read this file before producing any action frames. Design the motion information before allocating image detail.

## Action reference

Actively request an action reference when the user has not provided one and has not explicitly said that no action reference is needed. Accept:

- Video or gameplay capture
- GIF, APNG, or an existing spritesheet
- Ordered keyframes or frame-by-frame images
- Motion pose sheets, photography, or animation clips
- A precisely identifiable action from a game, film, animation, or real-world activity

Prefer a reference close to the target action, camera, body type, and rhythm; its art style may differ. Explain that the reference is used to read action phases, center-of-mass travel, contacts, limb arcs, holds, and event timing. It does not replace the character identity or project art direction.

Record from the reference:

- Start, anticipation, main action, extreme, recovery, and terminal states
- Total duration, rhythm changes, and deliberate holds
- Root motion, center of mass, contacts, and motion arcs
- Camera, direction, near and far limbs, and occlusion
- Hit, release, landing, or interaction events

When the user explicitly says no action reference is needed, treat that statement as authorization to design from written intent. Skip the reference request and search, then present the action phases, key poses, and timing chart before generating a full frame sequence.

When the user cannot provide a reference but has not declined references, read [reference-search.md](reference-search.md), proactively search Pinterest, and submit screened candidates. If references are incomplete, conflict with one another, or disagree with the runtime contract, explain the exact conflict and ask the user to choose. Only when Pinterest also yields no usable reference should you ask whether the user authorizes design from written intent. After authorization, present the action phases, key poses, and timing chart before generating a full frame sequence.

## General motion grammar

Record for every clip:

- State intent, direction, camera, and entry condition
- Loop, one-shot, terminal hold, or transition behavior
- Root-motion or in-place playback policy
- Key poses, motion arcs, contacts, and center-of-mass path
- Total duration, per-frame durations, and deliberate holds
- Gameplay event frames such as hit, release, landing, or interaction completion
- Anchor, baseline, canvas overflow rules, and effect bounds

Make key poses carry the information: anticipation explains what is about to happen, the main action or extreme explains what happens, and recovery or the terminal pose explains what follows. In-betweens only connect that information clearly.

## Action branches

### Idle and looping secondary motion

Keep the state recognizable and contact points stable. Offset the phases of breathing, blinking, cloth, and accessories to avoid synchronized piston motion across the whole body. A loop may use a repeated closing frame or transition naturally from the last frame to the first; follow the runtime contract.

### Walk and run

Define at least the contact, down, passing, and up phases, including the left-right foot order. Decide whether the character moves in place or carries root motion within the frames. Running usually needs shorter contacts, longer airborne intervals, and stronger counter-rotation through the torso. Keep cadence and visual mass consistent across directions while handling near- and far-side limb occlusion correctly.

Before producing a walk cycle, inspect [walk-cycle-reference.png](../assets/walk-cycle-reference.png). Use its CONTACT, RECOIL, PASSING, and HIGH-POINT phases to verify contact order, center-of-mass rise and fall, counter-swinging arms, and the explicit loop closure. Treat it as a motion-structure reference, not a template for character proportions or art style.

### Attack, cast, and interaction

Separate anticipation, action, and recovery; mark the hit, release, or interaction-completion frame. Weapons, arms, body, and effects must share a coherent arc and direction. Establish force with a small number of strong keyframes. If a smear is needed, treat it as a controlled effect layer rather than a substitute for a readable character pose.

### Jump, fall, and land

Separate takeoff, rise, apex, fall, and land. During airborne phases, the soles are no longer a stable baseline; align by the root or body center of mass instead. Declare whether the jump is in place or carries displacement. Landing frames must show compression, contact, and the following transition.

### Hurt, knockdown, and death

Make impact direction and silhouette readable before adding recoil or a state change. Knockdown and death may change the baseline and occupied area, but anchor semantics and collision events must remain synchronized. Death is usually a one-shot terminal state and should loop only when the runtime explicitly requires it.

## Direction and mirroring

Decide whether mirroring is safe before using it. Hair parts, garment fasteners, text, emblems, scars, weapon hand, sheath position, and lighting direction may require independent directional assets. Even when mirroring is approved, validate equipment handedness, attack arcs, and event hotspots independently.

All directions share:

- The same frame phases and overall rhythm
- The same visual mass and root semantics
- Corresponding contact, hit, release, and landing events
- Direction-correct occlusion and asymmetric details

## Key-pose gate

Before generating all in-betweens, present the key poses for each direction side by side and verify:

1. The action and direction are recognizable from silhouette alone.
2. Identity, proportions, equipment, and art treatment remain consistent.
3. Center of mass, contacts, and motion arcs are continuous.
4. Extreme poses and effects remain within the contract bounds.
5. Gameplay event frames show clear visual cause and effect.

Completion criteria: the action reference or the user's explicit opt-out or authorization for independent design is recorded, the key poses and timing chart for every clip are approved, and only constrained connection work remains for the in-betweens.
