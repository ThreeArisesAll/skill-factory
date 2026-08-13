# Production Delivery v2

`spritesheet-production-delivery/v2` seals one exact `spritesheet-package/v5` with the evidence required to reproduce its current production claim.

## Closed evidence set

The delivery contains job-relative, hash-bound references to:

- Approved `identity-bible/v2`
- Approved complete `motion-plan/v2`
- One `raw-frame-admission/v1` for every unique concrete high-resolution source
- Exact v5 package manifest and closed package-tree hash
- `motion-diagnostics/v2` and its generated presentation assets
- Approved `review-packet/v1`
- The mechanical quality policy used for raw admission and target-cell centroid steps
- An exact file inventory excluding `delivery.json` itself

Runtime integration is not represented by v2. Current production accepts `runtime_scope: null`; use [runtime-integration.md](runtime-integration.md) as a separately authorized downstream workflow.

## Independent replay

Sealing and verification require all of the following:

1. Identity and motion-plan approvals bind their exact canonical content.
2. The motion plan binds the identity hash and exactly matches package clips, views, positions, aliases, durations, and events.
3. Raw admissions cover every concrete plan source exactly once and bind plan, position, canonical view, packaged high-resolution bytes, Alpha measurements, transparent-RGB policy, and margin policy.
4. Package v5 passes full pixel and tree replay.
5. Diagnostics bind the package and every recorded metric recomputes from final sheet pixels.
6. The review packet exactly covers identity, motion plan, diagnostics, and package with acceptable observations and bound presentation assets.
7. The delivery tree contains exactly its declared semantic evidence and no symlinks or undeclared files.

The sealed quality policy also enforces the configured maximum target-cell Alpha-centroid step. This is a coarse mechanical discontinuity gate, not proof of root motion or contact quality.

## Claim boundary

Report the current classification of every conclusion:

- `MACHINE-VERIFIED`: schema, hashes, closed trees, admissions, package rendering, assembly, and recomputed measurements
- `REVIEWED`: identity, motion-plan, source-set, sequence, and package decisions explicitly covered by human review
- `DECLARED`: artistic intent, action meaning, metadata meaning, and generative relationships not directly proven by pixels
- `SUPPLIED`: external evidence whose presence and binding are checked without claiming direct observation

The only v2 delivery state is `package-ready`. A missing, stale, or failed requirement means no delivery state is achieved, even if the inner package remains independently pixel-verifiable.

## Invalidation

Regenerate the v2 delivery whenever a referenced hash, plan, source admission, package, diagnostic, quality policy, presentation, observation, or decision changes. Preserve independently valid upstream evidence and package bytes when their bound inputs are unchanged. Never rebind a changed diagnostic or review hash without replaying its semantic evidence; the verifier intentionally recomputes measurements from the package.
