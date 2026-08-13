---
name: create-better-spritesheet
description: "Create, rebuild, diagnose, review, or integrate high-fidelity 2D character sprite-sheet packages and their runtime metadata."
---

# Create Better Spritesheet

Route the request internally. Infer the route from the requested outcome and the live artifacts; never ask the user to choose a mode:

- **Create**: establish or reuse an exact valid canonical, then establish motion, sequence, and package evidence.
- **Rebuild**: start at the earliest changed or invalidated input and regenerate every dependent result.
- **Diagnose**: locate the owning source, rendering, metadata, or runtime defect and stop after diagnosis unless correction is requested.
- **Review**: evaluate supplied artifacts and evidence without changing them.
- **Integrate**: update a live runtime only when replacement or integration is explicitly requested.

Use the production seam for stateful work and the delivery seam for evidence work:

```bash
<python> <skill-dir>/scripts/spritesheet_production.py advance|verify
<python> <skill-dir>/scripts/spritesheet_delivery.py diagnose|seal-delivery|verify
```

Treat `spritesheet_pipeline.py prepare-canonical|build-package|verify-package` as a compatibility and internal-adapter surface. Use it directly only for scoped pixel-contract work, never as the primary production workflow. Treat CLI behavior and tests as authoritative for exact schemas and layout. Read each directly relevant reference before acting:

- [quality-contract.md](references/quality-contract.md) — resolve the production contract, style profile, quality gates, and correction owner.
- [approval-protocol.md](references/approval-protocol.md) — present, pause, record, invalidate, and serialize every approval.
- [production-interface.md](references/production-interface.md) — invoke the stateful production job, answer checkpoints, and verify a subject.
- [motion-design.md](references/motion-design.md) — design an action topology, motion blueprint, keyframes, spacing, and in-betweens.
- [reference-search.md](references/reference-search.md) — discover action evidence when the user cannot supply it.
- [lineage-evidence.md](references/lineage-evidence.md) — prepare canonical evidence, bind approved sources, build, and replay the package.
- [production-delivery.md](references/production-delivery.md) — assemble job evidence around the pixel package and determine the achieved delivery state.
- [silhouette-outline.md](references/silhouette-outline.md) — apply an enabled silhouette outline to canonical and frame high-resolution buffers.
- [optical-sizing.md](references/optical-sizing.md) — diagnose and correct native-size readability.
- [runtime-integration.md](references/runtime-integration.md) — project metadata and validate a requested live integration.

## Create sequence

1. Resolve one authoritative production contract and the applicable action topology. The installed executable profile is `smooth-raster/v1`.
2. **Canonical gate:** reuse only an exact, fully admitted, currently approved canonical whose bound inputs match; otherwise prepare, replay-admit, and approve one neutral canonical per required camera or direction.
3. **Motion-blueprint gate:** produce and approve the complete motion blueprint before generating motion images.
4. **Keyframe gate:** generate the topology's necessary keyframes, finalize their Alpha boundaries, and obtain the hash-bound keyframe-set approval.
5. **Spacing-plan gate:** derive and approve the complete `spacing-plan/v1` from the approved keyframes before generating in-betweens.
6. **Sequence gate:** generate the planned in-betweens, finalize Alpha boundaries, review the complete sequence, and obtain the hash-bound `sequence-approval`.
7. Build the package, replay verification, and inspect the complete diagnostic presentation at native size.
8. **Package-review gate:** approve the exact verified package, diagnostics, and presentation subjects before sealing the delivery. Correct defects at their owning stage and repeat every invalidated descendant.
9. Integrate only when authorized, update interdependent runtime contracts atomically, and validate the real production entry point.

Complete each step only when its referenced contract says the current evidence satisfies the step and every required approval is valid. Preserve resolved production decisions unless current evidence conflicts with them.

## Rebuild, diagnose, and review

For a rebuild, compare current hashes, contracts, and approvals to the requested change. Resume at the earliest invalid node in the create sequence; retain only evidence whose bound inputs remain exact.

For diagnosis or review, inspect the same lineage in order and classify each conclusion as `MACHINE-VERIFIED`, `REVIEWED`, `DECLARED`, `SUPPLIED`, or unresolved. Report the earliest owning defect and its invalidation impact. Keep diagnosis and review read-only unless the user also requests correction.

Return typed `UNSUPPORTED_CAPABILITY` for pixel-art create or rebuild because no pixel-art production adapter is installed. Diagnose and review pixel-art artifacts read-only when requested.

## Completion and handoff

Report the highest achieved output state from [production-delivery.md](references/production-delivery.md) only when its evidence passes:

- `package-ready`
- `runtime-metadata-complete`
- `runtime-verified`

For diagnosis or review that reaches none of these states, report `no delivery state achieved`.

Also report the route taken, applicable profile, supplied evidence, approvals, machine verification, visual findings, changes, tests, and remaining uncertainty as separate facts. Keep staging, committing, publishing, and production replacement outside scope unless requested.
