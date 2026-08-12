# Deterministic Silhouette Outline

Use this workflow only during canonical-master generation after the resolved master-outline contract enables an outer silhouette outline. Add the outline to the fixed-size high-resolution pre-master and lock the outlined result as the canonical master. Treat the unoutlined pre-master as a temporary source. Use the canonical master only as the final visual reference for later high-resolution keyframe generation; never use a generated keyframe, generated in-between, target frame, rendered frame, or assembled sheet as input to this workflow.

## Outline contract

1. Use the resolved outer silhouette outline width and derive its color from the art rules or neighboring production assets.
2. Convert the script parameter with `master radius = round(target-pixel radius × 512 / target short side)`.
3. Place the outline behind the character layer so every nontransparent source pixel remains byte-identical.
4. Use the added width only to improve silhouette recognition; keep internal structure lines at their original weight.
5. Lock the outlined output as the canonical master so every generated high-resolution keyframe uses the same final outline reference.

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

The input dimensions must match the fixed master dimensions derived from the target frame: the short side is exactly `512 px`, and the proportional long side is rounded to the nearest whole pixel. The script creates the outline on that input and emits only the outlined canonical master as a production-capable RGBA image. It performs an in-memory target-size review downsample for bounds and margin metrics, but does not emit a standalone target frame. It also emits opaque RGB review contact sheets and metrics JSON, and refuses to overwrite a nonempty directory.

## Accept

1. Confirm that the script reports `opaque interior pixel-identical: True`.
2. Compare source and outlined versions in the opaque native-size RGB review contact sheet, then use the opaque checkerboard-backed `4×` sheet to locate edge problems. Treat both contact sheets as non-production evidence.
3. Confirm that visual mass, center, and baseline are unchanged. Only the Alpha bounds may expand outward because of the outline.
4. Confirm that all four safe margins satisfy the live contract.
5. Inspect narrow gaps, limbs, equipment, and accessories for unnatural merging, jagged edges, halos, or transparent RGB contamination.
6. Compare line width, color, and sampling with neighboring production assets to confirm that the outline belongs to the same art treatment.

Completion criteria: the outlined canonical master is locked before high-resolution keyframe generation; solid interior pixels remain locked; all safe-margin and transparency checks pass; and downstream production uses the canonical master only as the final visual reference for generating multiple high-resolution keyframes.
