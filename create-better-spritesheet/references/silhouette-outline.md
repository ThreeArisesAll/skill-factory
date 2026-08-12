# Deterministic Silhouette Outline

Use this workflow only during canonical-master generation after the resolved master-outline contract enables an outer silhouette outline. Add the outline to the fixed-size high-resolution pre-master, lock the outlined result as the canonical master, and only then derive or downsample production frames. Treat the unoutlined pre-master as a temporary source. A target-size frame, rendered frame, or assembled sheet is never a valid input to this workflow.

## Outline contract

1. Use the resolved outer silhouette outline width and derive its color from the art rules or neighboring production assets.
2. Convert the script parameter with `master radius = round(target-pixel radius × 512 / target short side)`.
3. Place the outline behind the character layer so every nontransparent source pixel remains byte-identical.
4. Use the added width only to improve silhouette recognition; keep internal structure lines at their original weight.
5. Lock the outlined output as the canonical master so outline and body deformation share one pixel source.

Color and width must come from the current project contract. When color evidence is missing, create a static comparison and ask the user to approve it. Do not import another project's default style.

## Run

Use a fresh output directory. Square frames may continue to use the `--frame-size` shorthand:

```bash
<python> <skill-dir>/scripts/add_silhouette_outline.py \
  --source <absolute-working-size-pre-master-source.png> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-outline> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --outline-radius <contract-master-radius> \
  --outline-color '<contract-rrggbb>' \
  --safe-margin <contract-safe-margin>
```

The input dimensions must match the fixed master dimensions derived from the target frame: the short side is exactly `512 px`, and the proportional long side is rounded to the nearest whole pixel. The script creates the outline on that input, locks the result as the outlined canonical master, and then downsamples that master to emit the target frame. The target frame is a derivative, never the input to the outline operation. The script also emits source comparisons and metrics JSON, and refuses to overwrite a nonempty directory.

## Accept

1. Confirm that the script reports `opaque interior pixel-identical: True`.
2. Compare source and outlined versions at native `1×`, then use a checkerboard-backed `4×` view to locate edge problems.
3. Confirm that visual mass, center, and baseline are unchanged. Only the Alpha bounds may expand outward because of the outline.
4. Confirm that all four safe margins satisfy the live contract.
5. Inspect narrow gaps, limbs, equipment, and accessories for unnatural merging, jagged edges, halos, or transparent RGB contamination.
6. Compare line width, color, and sampling with neighboring production assets to confirm that the outline belongs to the same art treatment.

Completion criteria: the outlined canonical master is locked before any production-frame generation or target-size downsample; every target frame derives from that master; solid interior pixels remain locked; and all safe-margin and transparency checks pass.
