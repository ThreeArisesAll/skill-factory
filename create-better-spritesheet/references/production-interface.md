# Production Interface

Use the public stateful CLI:

```bash
<python> <skill-dir>/scripts/spritesheet_production.py advance --job <absolute-job-dir> --intent <intent.json> --json
<python> <skill-dir>/scripts/spritesheet_production.py advance --job <absolute-job-dir> --response <response.json> --json
<python> <skill-dir>/scripts/spritesheet_production.py verify --subject <manifest-package-or-delivery> --json
```

Pass exactly one of `--intent` or `--response` to `advance`. Keep the job directory opaque except for presentation paths explicitly returned by the checkpoint.

## Intent v2

Use `spritesheet-production-intent/v2` for current create and rebuild jobs. Set `base_revision` to `null` for a new job and to the current revision for a material update. Provide:

- `identity.sources`: absolute source path plus unique ID, direction, and camera for each canonical view
- `identity.art_contract`: the fields in [art-direction-contract.md](art-direction-contract.md)
- `clips`: complete topology and every logical position defined by [motion-plan-contract.md](motion-plan-contract.md)
- `target`: frame size, origin, anchor, safe bounds, and optional columns
- `rendering_profile`: `smooth-raster/v2`, outline contract, and quality thresholds
- `output_scope`: optional absolute delivery directory
- `runtime_scope: null`

For diagnose and review, provide only schema, revision, mode, absolute subject, and `runtime_scope: null`. Unsupported production profiles return `UNSUPPORTED_CAPABILITY` rather than silently translating their rules.

## Checkpoints

Each result contains one complete current checkpoint with:

- Stable ID, job revision, context hash, kind, and question
- A closed dynamic `response_schema`
- The complete presentation required for that gate or input

Validate the response against the returned schema. Never reuse it for another revision. Current production follows canonical review, complete motion-plan review, keyframe input and review, optional in-between input, sequence review, package review, and package-ready completion.

If a clip has no in-between sources, the workflow skips the empty input gate and proceeds directly from keyframe review to complete sequence review. Holds and loop closure remain explicit logical aliases.

## Failure behavior

Typed failures identify the recovery owner:

- `STALE_JOB_REVISION` or `STALE_CHECKPOINT`: reload the current checkpoint; do not replay the stale write.
- `CANONICAL_VIEW_MISMATCH`: correct the clip-to-view contract before job creation.
- `RAW_FRAME_ADMISSION_FAILED`: correct or replace the high-resolution source; no review opens.
- `QUALITY_GATE_FAILED`: correct source placement or revise the explicit threshold; no package review opens.
- `UNSUPPORTED_CAPABILITY`: install or implement a matching profile adapter; do not coerce the request.
- `JOB_PROTOCOL_STALE`: start a current job from authoritative source evidence.
- `DELIVERY_VERIFICATION_FAILED`: inspect the nested report and return to the earliest stale evidence owner.

Transitions are locked and state commits last. Failed operations retain the previous committed state and remove newly published outputs owned by the failed transition. Exact unchanged intent replay is idempotent.

## Verification boundary

`verify` is read-only. It accepts a v4 or v5 manifest/package and a sealed v1 or v2 delivery. A verified package proves its pixel contract but does not achieve a delivery state. A v2 delivery achieves `package-ready` only when its independent replay report passes.
