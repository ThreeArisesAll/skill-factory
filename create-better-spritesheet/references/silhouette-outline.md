# Deterministic Silhouette Outline

Use this workflow only after the target-size static frame is approved, the project art treatment requires an outer outline, and animation production has not begun. Generate the outer outline by dilating Alpha while locking identity and interior detail.

## Outline contract

1. Measure the target-size outer-outline width and color from the art rules or neighboring production assets.
2. Convert the script parameter with `working-resolution radius = target-pixel radius × working-scale`.
3. Place the outline behind the character layer so every nontransparent source pixel remains byte-identical.
4. Use the added width only to improve silhouette recognition; keep internal structure lines at their original weight.
5. Generate animation from the outlined high-resolution master so outline and body deformation share one pixel source.

Color and width must come from the current project contract. When evidence is missing, create a static comparison and ask the user to approve it. Do not import another project's default style.

## Run

Use a fresh output directory. Square frames may continue to use the `--frame-size` shorthand:

```bash
<python> <skill-dir>/scripts/add_silhouette_outline.py \
  --master <absolute-approved-working-size-mother.png> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-outline> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --working-scale <working-scale> \
  --outline-radius <contract-working-resolution-radius> \
  --outline-color '<contract-rrggbb>' \
  --safe-margin <contract-safe-margin>
```

The script requires master dimensions exactly equal to target dimensions multiplied by the working scale. It emits the outlined master, target frame, source comparison, and metrics JSON, and refuses to overwrite a nonempty directory.

## Accept

1. Confirm that the script reports `opaque interior pixel-identical: True`.
2. Compare source and outlined versions at native `1×`, then use a checkerboard-backed `4×` view to locate edge problems.
3. Confirm that visual mass, center, and baseline are unchanged. Only the Alpha bounds may expand outward because of the outline.
4. Confirm that all four safe margins satisfy the live contract.
5. Inspect narrow gaps, limbs, equipment, and accessories for unnatural merging, jagged edges, halos, or transparent RGB contamination.
6. Compare line width, color, and sampling with neighboring production assets to confirm that the outline belongs to the same art treatment.

Completion criteria: the target frame has a restrained, project-consistent outer outline; solid interior pixels remain locked; and all safe-margin and transparency checks pass.
