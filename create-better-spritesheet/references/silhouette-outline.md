# Deterministic Silhouette Outline v3

Use this branch inside canonical authoring when the resolved production spec enables an outer silhouette outline. Treat the content-addressed original authoring source as replay evidence and the derived candidate as the only possible canonical-reference bytes.

## Resolve the contract

Interpret `target_width` as outward silhouette thickness in target pixels. Convert it for the fixed canonical canvas:

```text
canonical_width = round(target_width * 512 / target_short_side)
```

Resolve color from authoritative art rules or neighboring production assets. Present a comparison and ask only when color evidence is missing or conflicting. Require nonzero Alpha. Execute consistently resolved `enabled` and `target_width` values directly.

## Derive the candidate

Normalize the authoring source deterministically to the fixed canvas in memory. When outline is enabled, always expand that buffer's Alpha outward by the resolved canonical width and composite the ring behind it, regardless of visible edge linework in the source. Preserve every existing nontransparent normalized pixel, internal line weight, straight RGBA storage, and zero RGB beneath zero Alpha. Keep the normalized buffer ephemeral: write neither a file nor a graph node for it.

Treat visible linework, dark edge pixels, filenames, declarations, and human observation as aesthetic evidence. Prove execution only by replaying the declared normalization and outline algorithms from the evidence-bound inputs and obtaining the candidate bytes exactly.

Run `prepare-canonical` with `canonical-authoring-request/v3`. Require the direct outputs `canonical-reference-candidate.png`, `canonical-reference-evidence.json`, `canonical-admission-proof.json`, and content-addressed original authoring-source evidence. Require the proof to use `canonical-admission-proof/v1`. Use no alternate acceptance flag or execution-history assertion.

## Admit the candidate

Require admission to match all of the following:

1. Candidate SHA-256, decoded dimensions, and mode match the prepared candidate bytes.
2. Authoring-source SHA-256 and target geometry match the evidence record.
3. Authoring-source SHA-256, dimensions, and mode match its content-addressed replay bytes.
4. Normalization and outline algorithm identifiers match the required v3 algorithms.
5. Outline enabled state, `target_width`, color, and resolved high-resolution width match the production contract and replay.
6. Deterministic in-memory normalization and outline derivation from the replay source reproduce the candidate byte for byte.

Reject partial, stale, mismatched, or missing admission evidence. Reuse an existing approved canonical only when every admission subject matches the current request and replay succeeds. Otherwise rerun preparation and repeat dependent approvals.

After machine admission succeeds, review visual mass, center, baseline, anatomy, equipment, line hierarchy, safe margins, narrow gaps, jaggedness, halos, and target-size treatment as aesthetics. Bind approval to both the exact candidate hash and admission-proof hash. Any correction changes the candidate or proof and invalidates downstream approvals and package outputs.
