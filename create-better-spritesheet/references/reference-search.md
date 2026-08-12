# Action Reference Search

Run this workflow only when the user cannot provide an action reference but still wants reference discovery. Do not run it when the user explicitly says no action reference is needed. Do not ask for separate search permission. Proactively search Pinterest, then ask the user to approve a candidate.

## Search Pinterest

Use an available web or browser tool to search Pinterest directly. If Pinterest pages are inaccessible, require login, or load incomplete results, use web or image search restricted to `pinterest.com` and open the specific Pin.

Construct two to four narrow queries from the motion contract. Prefer English action terms:

- `<action> animation reference`
- `<action> key poses`
- `<action> cycle contact passing high point`
- `<direction or camera> <action> animation reference`
- `<body type or equipment> <action> motion reference`

Substitute the actual action, direction, camera, body type, equipment, and loop or one-shot semantics. Do not use a broad term such as `animation` or `character movement` as the only query.

## Clarity and value gate

Use the built-in [walk-cycle-reference.png](../assets/walk-cycle-reference.png) as the screening benchmark. Prefer references that provide:

- Native resolution sufficient to read joints, contacts, and silhouettes
- An unambiguous pose sequence or labeled key phases
- Stable camera, character scale, ground line, and travel direction
- Unobstructed limbs with readable near-far relationships and equipment arcs
- Anticipation, main action, extreme, recovery, or a complete loop
- Clean composition without watermarks, text, or decoration blocking the motion

Reject candidates with tiny thumbnails, unclear pose order, severely cropped limbs, inconsistent perspective or scale, duplicate-image collages, AI anatomy errors, or only finished art style without usable motion information. A single pose may supplement one extreme but cannot prove a complete action by itself.

## Present candidates to the user

Present the two to four most valuable candidates instead of returning an entire results page. For each candidate, provide:

- An accessible Pin or original-source link
- A thumbnail preview or clear content description
- The phases, direction, rhythm, or event decisions it supports
- The motion information it still lacks

Recommend one candidate and ask the user which reference to adopt. Before approval, perform motion analysis and key-pose planning only; do not generate the full frame sequence.

Use Pinterest only to discover motion references. Whenever possible, open the original source linked by the Pin and record the creator or source page. Use external images to analyze motion, rhythm, and pose; do not copy character identity, clothing, brand elements, or art style. Do not save third-party images into the repository or Skill assets unless the user requests it.

## Built-in walk-cycle reference

`assets/walk-cycle-reference.png` is the user-provided built-in reference. Its dimensions are `1145×337`, and its SHA-256 is `b85df770ed6528e2c16ba4817752a533af424b9c2fbe11520564484652c191fc`. Its original external provenance has not been confirmed.

The image presents two alternating half-cycles through nine side-view poses:

1. CONTACT
2. RECOIL
3. PASSING
4. HIGH-POINT
5. CONTACT
6. RECOIL
7. PASSING
8. HIGH-POINT
9. CONTACT, repeating the first footfall phase for explicit loop closure

Inspect this image before producing any walk cycle. Use it to evaluate contact order, center-of-mass rise and fall, counter-swinging arms, stride arcs, and loop phases. Character identity, body proportions, clothing, and final art treatment remain governed by the project references.

When the user cannot provide a walk reference, use the built-in image as the default usable reference while searching Pinterest for a closer match to the target camera, body type, speed, and equipment. If the search yields nothing more valuable, report that result and recommend the built-in image.
