---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, or review high-fidelity 2D character sprite-sheet production, with complete motion-plan approval, deterministic smooth-raster rendering, and replayable delivery evidence."
---

# Create Better Spritesheet

Use this Skill for character identity, animation planning, sprite-source review, deterministic sheet production, delivery verification, or diagnosis. Infer the route from the requested outcome and live artifacts; do not ask the user to choose an internal mode.

The installed create/rebuild adapter is `smooth-raster/v2`. Pixel art and other raster paradigms have different authoring and sampling rules: review them without conversion, but return `UNSUPPORTED_CAPABILITY` for create/rebuild until a matching production adapter exists.

## Public seams

Use the stateful seam for production and read-only verification:

```bash
<python> <skill-dir>/scripts/spritesheet_production.py advance|verify
```

Use the evidence seam for deterministic diagnostics, sealing, and independent replay:

```bash
<python> <skill-dir>/scripts/spritesheet_delivery.py diagnose|seal-delivery|verify
```

Resolve `<python>` to Python 3.10+ with NumPy and Pillow. Treat `spritesheet_pipeline.py prepare-canonical|build-package|verify-package` as an internal and compatibility adapter, not the primary production workflow.

Read the references required by the current route:

- [art-direction-contract.md](references/art-direction-contract.md) for identity, visual consistency, paradigm boundaries, and native-size review.
- [motion-plan-contract.md](references/motion-plan-contract.md) for topology, animation principles, position roles, direction continuity, and the complete pre-image plan.
- [approval-protocol.md](references/approval-protocol.md) for approval subjects, pauses, invalidation, and recovery.
- [smooth-raster-profile.md](references/smooth-raster-profile.md) for Alpha, outline, scaling, optical correction, and visual quality gates.
- [production-interface.md](references/production-interface.md) for intent, checkpoint, response, and typed failure behavior.
- [pixel-evidence.md](references/pixel-evidence.md) for package v5 lineage, aliases, receipts, diagnostics, and replay boundaries.
- [production-delivery.md](references/production-delivery.md) for the sealed v2 evidence closure and claim classifications.
- [reference-search.md](references/reference-search.md) only when usable action evidence is missing and discovery is wanted.
- [runtime-integration.md](references/runtime-integration.md) only when the user explicitly authorizes changes to a target runtime.
- [compatibility.md](references/compatibility.md) when inspecting or migrating v1/v4 jobs, packages, commands, or deliveries.

## Create and rebuild workflow

1. Resolve the production profile, target cell contract, required canonical views, art-direction contract, actions, directions, and delivery scope. Reuse already resolved outline settings unless current evidence conflicts.
2. Prepare and replay-admit one high-resolution canonical per required direction-camera view. Inspect high-resolution and native-size previews on white, dark, and checkerboard backgrounds. Ask for canonical approval only when the complete view set is eligible.
3. Build one complete `motion-plan/v2` covering every clip and every logical playback position. Present the full current plan and obtain explicit approval before accepting or producing any keyframe or in-between image. Any material plan revision invalidates image work and requires presentation and approval of the complete revised plan.
4. Accept the planned high-resolution keyframe sources through raw RGBA admission. Present and approve the complete keyframe set.
5. Accept the planned in-between sources, if any, through the same admission. Represent holds and loop closure as aliases with no new image source. Present and approve the complete ordered sequence.
6. Build `spritesheet-package/v5`, replay deterministic rendering and assembly, compute diagnostics, and enforce configured mechanical thresholds before opening package review.
7. Present the exact identity, motion plan, package, diagnostics, native-size board, onion skin, and playback previews. Record one complete package decision with an observation for every required subject.
8. Seal `spritesheet-production-delivery/v2` and independently verify its file closure, approvals, raw-source admissions, package replay, and diagnostics recomputed from final sheet pixels.

Stop at the current checkpoint whenever input, approval, or eligibility is missing. Do not generate images while the motion-plan gate is unresolved. Do not patch target cells or a finished sheet; correct the earliest owning source or contract and rebuild descendants.

## Diagnose and review

Keep the subject byte-for-byte read-only. Verify from the outer delivery inward when available; otherwise start from the package manifest. Classify each conclusion as `MACHINE-VERIFIED`, `REVIEWED`, `DECLARED`, `SUPPLIED`, or unresolved. Report the earliest owning defect, affected descendants, and whether correction was requested; diagnosis alone does not authorize modification.

## Completion

Report `package-ready` only when a sealed delivery passes independent verification. A bare package may be pixel-verified but has no delivery state. Separate machine results, human visual acceptance, declared intent, supplied external evidence, and unresolved uncertainty. Do not stage, commit, publish, replace runtime assets, or create a pull request unless separately requested.
