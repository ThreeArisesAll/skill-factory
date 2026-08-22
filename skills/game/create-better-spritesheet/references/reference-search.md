# Action Reference Search

Run this workflow only when the user cannot provide action evidence and still wants reference discovery. Skip it when the user explicitly declines action evidence. Search without a separate permission prompt, then use the [approval protocol](approval-protocol.md) before adopting a candidate.

## Search

Use available web or browser search. Pinterest may be useful for discovery, but prefer the original creator or source page whenever it is available. If a Pinterest page is inaccessible, requires login, or loads incomplete results, use web or image search restricted to `pinterest.com` and open the specific Pin.

Construct two to four narrow queries from the complete motion plan. Prefer English action terms:

- `<action> animation reference`
- `<action> key poses`
- `<action> contact passing extreme`
- `<direction or camera> <action> animation reference`
- `<body type or equipment> <action> motion reference`

Substitute the actual action, direction, camera, body type, equipment, and loop or one-shot behavior. A broad term such as `animation` alone is insufficient.

## Clarity and value gate

Use the original [walk-cycle-phases.svg](../assets/walk-cycle-phases.svg) as a terminology and screening aid for cyclic locomotion, not as observed performance evidence. Prefer external references that provide:

- Native resolution sufficient to read joints, contacts, and silhouettes
- An unambiguous pose sequence or labeled structural anchors
- Stable camera, character scale, ground line, and travel direction
- Unobstructed limbs with readable near-far relationships and equipment arcs
- The topology's causal phases, transitions, or complete loop
- Creator or source attribution and composition unobstructed by decoration

Reject candidates with tiny thumbnails, unclear pose order, severely cropped limbs, inconsistent perspective or scale, duplicate-image collages, implausible anatomy, or only finished art style without usable motion information. A single pose may support one anchor but cannot establish a complete action.

## Present candidates

Present the two to four most useful candidates rather than an entire result page. For each candidate, provide:

- An accessible original-source or Pin link
- A thumbnail preview or clear content description
- The topology, phases, rhythm, direction, or event decisions it supports
- The motion information it lacks

Recommend one candidate and present the complete current set for approval. Before approval, analyze motion and draft the complete motion plan only; generate no motion images.

Use external images to study motion, rhythm, and pose. Do not copy character identity, clothing, brand elements, or art style. Do not save third-party images into the repository or Skill assets unless the user requests it and rights are clear.

## Built-in educational diagram

`assets/walk-cycle-phases.svg` is an original, pure-SVG teaching diagram shipped with this Skill. It names five structural positions in a generic side-view walk half-cycle: contact, down, passing, up, and the next contact. Use it to explain terminology, support query construction, and screen whether a candidate exposes contact order, support transfer, center-of-mass change, and loop continuity.

Audit its embedded SVG provenance metadata: author `ThreeAA skill-factory refactor`, date `2026-08-13`, source `original geometric SVG`, license `repository terms`.

The diagram is deliberately schematic. It provides no character identity, body mechanics, timing, performance style, or production-ready pose evidence. Use supplied or discovered motion evidence for those decisions, or obtain explicit authorization to design them from written intent.
