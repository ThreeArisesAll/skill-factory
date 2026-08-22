# Compatibility and Migration

Current production uses intent v2, job v3, response v2, request v5, package v5, diagnostics v2, and delivery v2. Public command names remain stable.

## Retained read and verification support

The package retains these legacy contracts for existing callers and artifacts:

- `spritesheet-production-intent/v1`, job v2, and response v1
- `spritesheet-production-request/v4` and `spritesheet-package/v4`
- `identity-bible/v1`, `motion-blueprint/v1`, `spacing-plan/v1`, `motion-diagnostics/v1`, and `spritesheet-production-delivery/v1`
- Runtime projection and playback-proof v1 inside legacy delivery v1

Canonical authoring v3, canonical evidence v3, canonical admission proof v1, rendering receipt v2, and `smooth-raster-pixel-protocol/v3` remain current shared pixel contracts.

## Behavioral differences

| Legacy v1/v4 | Current v2/v5 |
| --- | --- |
| Separate motion blueprint and spacing-plan gates | One complete motion plan approved before any motion image |
| Adapter minimum of two keyframes and two in-betweens | Topology-driven position count with at least one concrete source |
| Repeated opening cell flag | Explicit `closing` alias |
| Every frame ID owns a distinct raster | Logical aliases reuse one earlier concrete source |
| Diagnostics are sealed but not recomputed during delivery replay | Every diagnostic cell metric is recomputed from final sheet pixels |
| Runtime states can be sealed in delivery v1 | Delivery v2 is package-ready only; runtime work is downstream and separately authorized |

## Migration

For new or materially revised work, start a v2 job from authoritative canonical sources and a complete v2 art and motion contract. Do not relabel a v4 manifest as v5 or translate legacy repeated cells into fabricated sources.

Existing v4 packages and v1 deliveries remain verifiable through the public CLIs. Preserve them when no material rebuild is requested. If migration is required, reconstruct the complete logical position list, convert repeated timing cells to explicit aliases, obtain complete motion-plan approval, readmit every concrete high-resolution source, and rebuild v5 plus delivery v2.

Treat direct `spritesheet_pipeline.py` use as compatibility or scoped pixel-contract work. Normal agents should enter through `spritesheet_production.py` so checkpoint, invalidation, and evidence rules remain enforced.
