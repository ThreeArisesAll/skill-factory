# Release Notes — v2.1124

## Release thesis

`v1.100` optimized observable human-style deliberation. `v2.1124` replaces imitation as the central metaphor with **asymmetry-aware hybrid cognition**.

The major claim is deliberately limited: current human cognition and current AI inference differ structurally in ways that matter for decisions, but those differences depend on the compared people, task, and deployed system. This release does not claim to settle consciousness, general intelligence, or a timeless essence of either category.

## New architecture

- BRIDGE protocol: Bind, Recognize, Import, Deliberate, Give judgment, Execute.
- Five claim levels: behavior, mechanism, functional state, experience, normative status.
- 32 operational human–AI asymmetry tracks.
- Explicit runtime inventory for model, context, modalities, retrieval, tools, memory, sensors, actuators, permissions, policies, and automation.
- Complementarity rule: exploit AI breadth and formalization; preserve human ownership of ends, lived context, consent, values, commitments, and consequence.
- Reality-contact rule: prefer observation, measurement, tool use, demonstration, prototype, experiment, and outcome feedback to additional verbal speculation.
- Anti-theater rules for anthropomorphism, raw chain-of-thought, unsupported confidence, sycophancy, and rationale-as-proof.
- Responsibility design: decision owner, authorization, veto, appeal, audit, rollback, remedy, and escalation.

## Iteration and evaluation

- Preserved the exact first 100 `v1.100` iteration records and hashes.
- Added 1024 records as 32 asymmetry tracks × 32 refinement passes.
- Total ordered records: 1124.
- Final chain hash: `85564233f6c04f1fa508b03366d19e33fe8f5dc6e70802ec4196d7fd62ab232c`.
- Added 32 track-specific behavior cases, anti-anthropomorphism cases, trigger prompts, CSV/JSONL live-eval fixtures, and a 16-dimension rubric.
- Deterministic checks validate structure and specifications only; they do not claim 1024 independent model runs.

## Packaging

- Canonical local install path: `~/.agents/skills/human-reasoning`.
- Compatibility symlink: `~/.codex/skills/human-reasoning`.
- ZIP contains one top-level `human-reasoning/` folder.
