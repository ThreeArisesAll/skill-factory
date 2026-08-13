# Deterministic Silhouette Outline

Use this reference when the resolved production spec enables an outer silhouette outline. Apply [approval-protocol.md](approval-protocol.md) when outline evidence is missing or conflicting. The same resolved visual contract serves two distinct pixel derivations: canonical preparation and deterministic frame rendering. A proof for one derivation never proves the other.

## Resolve the contract

Interpret `target_width` as outward silhouette thickness in target pixels. Convert it for a high-resolution source:

```text
high_resolution_width = round(target_width * high_resolution_short_side / target_short_side)
```

Resolve color from authoritative art rules or neighboring production assets. Present a comparison and ask only when color evidence is missing or conflicting. Require the enabled outline color Alpha to equal `255`, and require at least one Alpha-255 silhouette seed in every outlined source. Execute consistently resolved `enabled` and `target_width` values directly; reject an invalid color or seed set rather than emitting a transparent or empty ring.

## Canonical preparation

Canonical authoring remains v3. Before outline derivation, normalize the evidence-bound authoring source and apply the complete Alpha, outline-coverage, compositing, cleanup, and sampling equation in [lineage-evidence.md](lineage-evidence.md). After derivation, run the required post-derivation backing check. Only a zero unbacked count satisfies the canonical Alpha gate and permits admission. Keep the normalized and outlined buffers ephemeral.

Require the production seam's canonical step to emit the candidate, v3 evidence, v1 admission proof, content-addressed source evidence, and the complete canonical review-preview matrix. Its internal compatibility adapter may call `prepare-canonical`; use that command directly only for scoped pixel-contract work. Prove execution only by replaying the declared Alpha, normalization, and outline policies and reproducing the candidate bytes exactly.

This admission proves only the canonical candidate. The canonical later supplies identity, art direction, camera, and direction evidence; its silhouette ring does not propagate through image generation to a new pose.

## Deterministic frame rendering

Use each approved raw high-resolution frame source only after background removal, Alpha cleanup, crop placement, normalization, and optical correction are complete. Treat that final Alpha as authoritative source evidence. Apply the current deterministic high-resolution outline algorithm exactly as defined by [lineage-evidence.md](lineage-evidence.md), keep the outlined buffer ephemeral, and resize it exactly once to the target cell. The production contract remains authoritative for outline color.

When outline is disabled, use the declared identity operation in the lineage equation. A target cell and an assembled sheet are outputs, never outline authoring inputs.

## Review boundary

Machine replay proves that the deterministic ring was derived from the declared authoritative Alpha and reached the final sheet through the declared sampler and layout. It does not prove that the Alpha represents the intended body, that image generation obeyed the canonical, or that the result is aesthetically good.

Review canonical Alpha and its bound background previews under the admission and preflight contract in [lineage-evidence.md](lineage-evidence.md). Review raw frame Alpha for missing limbs, detached noise, background remnants, accidental transparency, narrow gaps, effect boundaries, and adequate margin. Review rendered target cells for line hierarchy, clipped rings, jagged steps, directional thickness spikes, square corners, bulges, halos, clogged gaps, temporal outline flicker, and native-size readability. Treat every listed outline defect as a hard blocker. Correct a mask defect in the canonical or raw source; correct a deterministic ring or clipping defect in the renderer or outline contract.
