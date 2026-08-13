# Production Interface

Use the stateful production seam exactly as exposed:

```bash
<python> <skill-dir>/scripts/spritesheet_production.py advance --job <job-dir> --intent <intent.json> --json
<python> <skill-dir>/scripts/spritesheet_production.py advance --job <job-dir> --response <response.json> --json
<python> <skill-dir>/scripts/spritesheet_production.py verify --subject <manifest-or-delivery> --json
```

Pass exactly one of `--intent` or `--response` to `advance`. Treat the job directory as opaque agent-managed state: retain its path, but do not inspect, edit, copy, or depend on its internal layout. You may open the exact presentation files explicitly returned by the current checkpoint; treat every other job-internal path as private.

## Initial intent

Submit one `spritesheet-production-intent/v1` document. Set `base_revision` to `null` for a new job and to the current job revision for any material update; stale updates fail with `STALE_JOB_REVISION`. An exact replay of unchanged intent is idempotent. For create and rebuild, provide only high-level production intent:

- Identity sources and identity declarations
- Clip topology intent and structural keyframes
- At least one action-evidence record per clip: either a supplied reference or explicit authority to design from written intent
- Target geometry and runtime-facing requirements
- Rendering profile ID `smooth-raster/v1` and its high-level outline choice
- `output_scope`, with optional `delivery_dir`
- `runtime_scope: null` because runtime integration is not currently supported by this production adapter

For diagnose and review, provide only the absolute regular-file or directory `subject` required by the intent schema. Do not place canonical v3 evidence, package v4 hashes or proofs, approval order, grid derivation, sampler settings, or other internal pixel-contract fields in the initial intent. The job derives and validates those details behind checkpoints.

## Checkpoints and responses

Treat every returned checkpoint as the complete current interaction contract. It contains:

- `id`
- `job_revision`
- `context_sha256`
- `kind`
- `question`
- `response_schema`
- `presentation`

Present the checkpoint's question and presentation without dropping governed subjects. Build the response by returning the exact checkpoint identity and revision fields required by `response_schema`, plus only the requested decision or input. Validate the complete response against that dynamic schema before calling `advance` again.

Never reuse a response for a different checkpoint or revision. A stale checkpoint, stale job revision, malformed response, unsupported capability, or unsupported pixel-art production request returns a structured typed error. Preserve its code and details when reporting or deciding the next action.

## Guarantees

- Repeating the same valid operation against the same revision is idempotent.
- Every accepted transition advances the job revision; material changes separately advance the artifact-lineage revision; stale writes are rejected.
- The state commit is last. A failed transition cannot advance state, and the previously committed material revision remains addressable.
- `verify` is read-only and accepts an immutable package manifest or sealed delivery subject. A bare v4 package may be pixel-package verified, but it has no delivery state until a sealed delivery passes the delivery verifier.
- Create and rebuild support only `smooth-raster/v1`; pixel-art production fails with typed `UNSUPPORTED_CAPABILITY`.
- The retained v4 pixel adapter requires at least two distinct keyframes and two distinct in-betweens per clip. This is an adapter encodability limit, not an artistic planning rule; an otherwise approved topology outside it fails with typed `LEGACY_TOPOLOGY_UNSUPPORTED` rather than being padded with invented poses.
- Diagnose and review keep their subject read-only.
- A completed production job or verified pixel package alone is not `package-ready`. Report `package-ready` only after the delivery has been sealed through `spritesheet_delivery.py seal-delivery` and that sealed delivery passes verification.
