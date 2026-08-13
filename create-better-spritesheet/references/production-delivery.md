# Production Delivery v1

Use `spritesheet-production-delivery/v1` as the job and delivery envelope around one exact verified `spritesheet-package/v4`. Seal and verify it through `spritesheet_delivery.py`. The envelope records intent, reviews, diagnostics, and supplied runtime evidence without expanding or reinterpreting the pixel package.

## Authority boundary

`spritesheet-package/v4` remains the sole authority for packaged source bytes, manifest metadata, canonical admission material, deterministic rendering, sheet assembly, hashes, and pixel replay. A valid v4 package proves its declared pixel derivation. It does not prove identity intent, motion quality, metadata meaning, review presentation, an external runtime projection, or runtime playback.

The v1 delivery envelope references one exact v4 package and these job-level evidence schemas:

- `identity-bible/v1`: approved identity, art direction, camera, direction, and recognition constraints
- `motion-blueprint/v1`: approved topology, phases, structural anchors, timing intent, events, and transitions
- `spacing-plan/v1`: approved playback positions, keyframe brackets, durations, events, and spacing intent
- `motion-diagnostics/v1`: measured package properties, generated review assets, ownership classification, and correction consequences
- `review-packet/v1`: exact subjects, presentation assets, observations, and recorded human decision
- `spritesheet-runtime-projection/v1`: closed projection of the exact package geometry, assembly, cells, clips, timing, and events into an external runtime contract
- `runtime-playback-proof/v1`: supplied target-runtime evidence and recorded playback, event, and rendering checks

Treat these as closed evidence schemas, not v4 manifest sections. Use executable schemas for exact fields. This document is the sole authority for their delivery roles and invalidation relationships.

## Dependency and invalidation

Bind the envelope to the exact v4 package and exact evidence hashes. Apply [approval-protocol.md](approval-protocol.md) to every human decision.

An outer evidence change never alters or invalidates unchanged v4 pixel bytes, manifest bytes, or pixel replay. It may make the current delivery binding or eligibility stale:

- An identity-bible change makes canonical approval and all dependent motion, review, delivery, and runtime evidence ineligible until reconciled. Rebuild v4 only when canonical or packaged inputs actually change.
- A motion-blueprint change makes affected keyframe, spacing-plan, sequence, diagnostic, review, delivery, and playback bindings ineligible. Rebuild v4 only when raw sources or manifest content change.
- A spacing-plan change makes affected sequence, manifest-metadata semantics, review, delivery, runtime projection, and playback bindings ineligible. Unchanged pixels remain replayable even when their current delivery meaning is stale.
- A raw-source, rendering-contract, assembly, or v4 manifest change requires a new exact pixel-package binding and invalidates every delivery claim bound to the prior package.
- A review-packet presentation change makes its recorded decision ineligible when it changes what the authority could inspect; unchanged production bytes remain valid.
- An external runtime contract, projection, environment, integration, or playback change makes affected runtime evidence and higher delivery eligibility stale; a still-matching v4 package remains independently verifiable.

Regenerate the envelope whenever a referenced hash changes. Retain no output state whose required current bindings and evidence fail.

## Metadata boundary

Distinguish metadata inside the v4 manifest from metadata projected into a consumer runtime:

- Verify v4 manifest schema, hashes, internal references, and pixel/package bindings as `MACHINE-VERIFIED`.
- Treat the intended semantics of clip names, timing, anchors, events, loops, and transitions as `DECLARED` unless explicitly `REVIEWED`.
- Treat an external runtime projection as a separate delivery input. Verification may prove its schema and binding to the exact manifest, while its semantic correctness remains `DECLARED` or `REVIEWED`.

## Output states

Report a state only when the delivery verifier passes all of its required current evidence:

| State | Required evidence | Claim boundary |
| --- | --- | --- |
| `package-ready` | Verified v4 pixel package, current identity, blueprint, spacing, diagnostics, review coverage, and approvals | Package replay and delivery bindings pass; visual and metadata conclusions retain their recorded classifications |
| `runtime-metadata-complete` | `package-ready` plus a current external runtime contract and manifest-bound projection | Projection schema and binding pass; metadata semantics are `DECLARED` or `REVIEWED`, not inferred by the verifier |
| `runtime-verified` | `runtime-metadata-complete` plus current `runtime-playback-proof/v1` | Runtime evidence is `SUPPLIED`; the verifier checks its schema, hashes, assets, bindings, and recorded check results without claiming direct runtime observation |

The states are cumulative. Report a lower state when a higher state's evidence is missing, stale, conditionally skipped, or unresolved. For diagnosis or review that meets none, report `no delivery state achieved`. Never infer runtime observation from package replay, metadata inspection, or a verifier pass.
