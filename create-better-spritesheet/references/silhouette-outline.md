# Deterministic Silhouette Outline v2

Use this branch only inside canonical authoring when the resolved production spec enables an outer silhouette outline. The outlined image becomes the canonical-reference candidate presented for approval. The unoutlined buffer and comparison evidence remain outside the production graph.

## Contract

`target_width` means outward silhouette thickness in target-size pixels. Convert it internally for the fixed canonical canvas:

```text
canonical_width = round(target_width * 512 / target_short_side)
```

Derive outline color from authoritative art rules or neighboring production assets. When color evidence is missing or conflicting, present a static comparison and ask the user to choose. The enabled request includes an RGBA color with nonzero Alpha. Keep consistently established enabled state and `target_width` without reconfirmation.

Place the outline behind the character so existing nontransparent source pixels remain byte-identical. Expand only the outer silhouette; preserve internal structure-line weights. Process Alpha in premultiplied-alpha space and store the resulting PNG as straight RGBA with zero RGB beneath zero Alpha.

## Prepare and accept

Run `prepare-canonical` with a `canonical-authoring-request/v2`; use CLI help for exact fields. Review outputs may include metrics and contact sheets, but only the approved final candidate can enter production.

Accept when:

1. Existing nontransparent source pixels are byte-identical.
2. Alpha expands outward by the resolved canonical width and all safe margins pass.
3. Visual mass, center, baseline, anatomy, equipment, and internal lines remain stable.
4. Narrow gaps, limbs, and accessories avoid unintended merging, jaggedness, halos, and transparent-RGB contamination.
5. Width, color, and sampling match the current project's art treatment.

`canonical-approval` binds the accepted candidate's exact SHA-256 hash. Any outline correction creates a new candidate and invalidates all downstream approvals and package outputs.
