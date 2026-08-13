# Deterministic Silhouette Outline

Use this reference when the resolved production spec enables an outer silhouette outline. The same resolved visual contract serves two distinct pixel derivations: canonical preparation and deterministic frame rendering. A proof for one derivation never proves the other.

## Resolve the contract

Interpret `target_width` as outward silhouette thickness in target pixels. Convert it for a high-resolution source:

```text
high_resolution_width = round(target_width * high_resolution_short_side / target_short_side)
```

Resolve color from authoritative art rules or neighboring production assets. Present a comparison and ask only when color evidence is missing or conflicting. Require nonzero source Alpha. Execute consistently resolved `enabled` and `target_width` values directly.

## Canonical preparation

Canonical authoring remains v3. Normalize the evidence-bound authoring source to the fixed canonical canvas in memory. Always expand that buffer's Alpha outward by the resolved width and composite the ring behind it, regardless of visible edge linework. Keep the normalized buffer ephemeral.

Require `prepare-canonical` to emit the candidate, v3 evidence, v1 admission proof, and content-addressed source evidence. Prove execution only by replaying the declared normalization and outline algorithms and reproducing the candidate bytes exactly.

This admission proves only the canonical candidate. The canonical later supplies identity, art direction, camera, and direction evidence; its silhouette ring does not propagate through image generation to a new pose.

## Deterministic frame rendering

Use each approved raw high-resolution frame source only after background removal, Alpha cleanup, crop placement, normalization, and optical correction are complete. Treat that final Alpha as the authoritative pose silhouette.

For each unique raw source, derive the output in memory:

1. Expand the authoritative Alpha outward by the resolved high-resolution width.
2. Subtract the original Alpha to obtain the outer ring.
3. Composite the resolved color behind every existing nontransparent source pixel.
4. Preserve internal linework, straight RGBA storage, and zero RGB beneath zero Alpha.
5. Resize the outlined high-resolution buffer exactly once with the declared premultiplied-Alpha sampler into the target cell.

Keep the outlined high-resolution buffer ephemeral. Bind the source hash, mask policy, algorithm, resolved width, sampler, outlined-buffer hash, target-cell hash, and final sheet hash through the manifest's top-level `spritesheet-rendering-receipt/v1` rendering object; the production contract remains authoritative for outline color. Verification must replay the complete batch and reproduce the final spritesheet exactly.

When outline is disabled, use the declared identity operation before the same single-resize path. A target cell and an assembled sheet are outputs, never outline authoring inputs.

## Review boundary

Machine replay proves that the deterministic ring was derived from the declared authoritative Alpha and reached the final sheet through the declared sampler and layout. It does not prove that the Alpha represents the intended body, that image generation obeyed the canonical, or that the result is aesthetically good.

Review raw Alpha for missing limbs, detached noise, background remnants, accidental transparency, narrow gaps, effect boundaries, and adequate margin. Review rendered target cells for line hierarchy, clipped rings, jaggedness, halos, clogged gaps, flicker, and native-size readability. Correct a mask defect in the raw source; correct a deterministic ring or clipping defect in the renderer or outline contract.
