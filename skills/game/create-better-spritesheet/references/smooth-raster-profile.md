# Smooth Raster Profile v2

`smooth-raster/v2` is the installed create/rebuild profile. It authors antialiased RGBA at high resolution and derives target cells through `smooth-raster-pixel-protocol/v3`.

## Authoritative lineage

For every concrete frame source, use exactly:

```text
final high-resolution RGBA source
-> optional deterministic outward outline on the high-resolution buffer
-> one lanczos-premultiplied-v1 resize to target cell
-> transparent-RGB cleanup
-> deterministic cell assembly
```

The target cell and finished sheet are immutable outputs. Never apply an outline, Alpha cleanup, optical correction, or second resize to either. A canonical outline proves only its canonical candidate; each new action pose has an independent high-resolution source and independent deterministic render.

## Canonical preparation

Canonical authoring uses `canonical-authoring-request/v3`, `canonical-reference-evidence/v3`, and `canonical-admission-proof/v1`. The canonical canvas has a 512-pixel shortest side. Preparation must:

1. Snapshot the source as a regular non-symlink file.
2. Normalize it with `normalize-to-canvas/lanczos-premultiplied-v1`.
3. Remove exterior low-Alpha residue under the evidence-bound policy.
4. Apply `outward-silhouette-euclidean-coverage-opaque-alpha/v3` when outline is enabled.
5. Require opaque Alpha seeds, opaque outline color, adequate border margin, and no unbacked partial-Alpha boundary.
6. Emit candidate, evidence, proof, and six review composites atomically.
7. Replay the proof and candidate bytes before opening canonical review.

Review the high-resolution candidate and native target preview on white, dark, and checkerboard backgrounds. White fringe, detached residue, jagged steps, square corners, outline bulges, clipped borders, or directional thickness spikes block approval.

## Raw frame admission

Every concrete `keyframe` or `in-between` is admitted before visual review through `raw-frame-admission/v1`. Admission proves:

- Exact binding to the approved `motion-plan/v2` and position
- Required high-resolution canvas and RGBA PNG format
- Nonempty Alpha and configured high-resolution margin
- Transparent RGB rejection with no hidden color beneath zero Alpha
- File hash, decoded RGBA hash, Alpha bounds, margins, opaque and partial-Alpha counts, and weighted Alpha centroid

Aliases have no raw source and no admission record. Delivery replay reopens the packaged high-resolution source and recomputes its measurable admission facts.

## Mechanical quality policy

`quality_thresholds` contains:

- `transparent_rgb`: `reject`; normalization evidence is intentionally unsupported
- `minimum_margin`: minimum high-resolution transparent margin on every side
- `maximum_alpha_centroid_step`: maximum Chebyshev displacement, in target pixels, between consecutive logical cells

These gates detect contamination, clipping risk, and large spatial jumps. Alpha centroid is not a skeleton root, support-foot tracker, or artistic center of mass. Root motion, planted contacts, foot slide, landing, weight, and intentional traversal remain plan-bound visual-review decisions.

## Optical correction

At native `1x`, inspect recognition, silhouette, negative space, occupied size, baseline, palette grouping, line hierarchy, equipment, contact readability, and temporal edge stability. When reduction loses important information, correct the owning high-resolution canonical or action source by consolidating microdetail or strengthening large-form separation. Preserve approved identity and plan intent.

Temporal outline flicker, halos, clogged gaps, or inconsistent edge hierarchy block sequence or package approval. Correct inconsistent source Alpha at the source; correct deterministic ring, sampler, or clipping defects in the renderer or profile contract.

## Runtime presentation

Use smooth filtering and permit non-integer placement only when the target project supports it. Do not convert a smooth-raster package into pixel art by changing a runtime filter. Inspect live engine rules before integration.
