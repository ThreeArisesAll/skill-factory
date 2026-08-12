# Target-Size Optical Correction

Use this workflow when the high-resolution master, premultiplied Alpha, single high-quality downsample, and runtime sampling are all correct, yet the character remains unclear at native size. The goal is to redraw the information hierarchy, not to manufacture extra edge contrast.

## 1. Diagnose the real pixel budget

1. Calculate the character bounds on the final frame with `alpha > 8`; record occupied width, height, and all four margins.
2. Inspect project-defined identity anchors at native `1×`. Use `4×` only to locate pixel competition.
3. Distinguish three problem classes:
   - Jagged edges or halos: return to the sampling and transparency chain.
   - Global softness: inspect runtime, canvas, CSS, or actual scaling.
   - Smooth edges with crowded information: proceed to optical correction.
4. Record the original target-size bounds. Keep the same canvas, visual mass, center, and baseline in later candidates so enlarging the character cannot masquerade as improved clarity.

Completion criteria: identify which shapes compete within the occupied pixels instead of attributing the problem generally to low resolution.

## 2. Edit one static high-resolution candidate

Use the approved identity reference, art reference, and current transparent source frame as simultaneous constraints. Edit only one static candidate, preferably the hardest-to-read key pose. Preserve identity, action intent, proportions, composition, palette, and carried items.

Design the high-resolution image for the final target size:

- Read the target pixel width of the outer silhouette outline and important internal structure lines from neighboring production assets.
- Consolidate flyaway hair, folds, laces, hardware, and similar microdetails into a few stable shapes.
- Increase value or hue separation between identity anchors within the tonal hierarchy allowed by the project art direction.
- Preserve the project's antialiasing, line weight, material treatment, and silhouette language.
- Spend precision on large-form boundaries and identity anchors; make microtexture yield to the remaining pixel budget.

If the first edit retains too much microdetail, perform one bounded second pass that simplifies only line hierarchy, detail density, and value grouping without changing identity or composition. Then stop generating equivalent candidates.

Completion criteria: the high-resolution candidate agrees with the approved references and its shape design clearly serves the target size.

## 3. Create and validate transparency

Prefer transparent generation. When a color key is required, choose a flat solid color outside the character palette and remove it with a reliable color-key tool. Inspect the tool parameters first and tune thresholds against the actual edge instead of reusing constants from another image.

After every transparency operation, verify:

- Corner Alpha values are zero.
- The `alpha > 8` bounds do not fill the canvas.
- Thresholding has not removed character colors.
- Edges contain no key-color residue, white or black fringe, or translucent haze.
- RGB is zero beneath fully transparent pixels.

A transparency viewer may render correct transparent areas as black. Composite the RGBA image over neutral gray and checkerboard backgrounds, then sample suspicious RGBA pixels before deciding that content is missing.

Completion criteria: the Alpha bounds are clean, edge colors are intact, and no background residue remains.

## 4. Normalize and generate comparisons

Run in a fresh output directory. Square frames may continue to use the `--frame-size` shorthand:

```bash
<python> <skill-dir>/scripts/prepare_optical_candidate.py \
  --source-alpha <absolute-high-resolution-rgba-candidate> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-optical> \
  --original <absolute-original-target-frame> \
  --sharpened <absolute-optional-sharpened-target-frame> \
  --frame-width <contract-frame-width> \
  --frame-height <contract-frame-height> \
  --margin <contract-safe-margin>
```

When using a color key, also pass `--key-rgb R G B` to report the residual-color ratio. The script validates transparent boundaries, normalizes the candidate onto the working canvas in premultiplied Alpha, downsamples only once, and emits the normalized high-resolution candidate, target-size comparison control, metrics JSON, native-size comparison, and checkerboard-backed `4×` comparison. Treat the normalized high-resolution candidate as a pre-master until its resolved outline treatment is complete; only then may it become the canonical master. `--sharpened` is an optional control, not a production stage.

When the resolved master-outline contract enables an outer silhouette outline, treat the emitted unoutlined high-resolution file as the temporary pre-master and its unoutlined target-size derivative as a comparison control only. Run the silhouette-outline workflow on the high-resolution pre-master within this candidate's master-generation step. Lock the outlined result as the canonical master before deriving the outlined target frame for approval. Never add the outline to the target-size candidate itself.

Completion criteria: candidate and controls have identical dimensions, the candidate bounds retain comparable visual mass to the original, and every output derives from the same high-resolution candidate.

## 5. Approve the static gate

Present images side by side in a fixed order: original, optional mild sharpening, and optical correction. Inspect native `1×` first, then use `4×` to explain differences. Evaluate whether:

- Identity anchors read faster.
- Lines are more stable rather than merely darker, harder, or haloed.
- Value groups are clearer while remaining faithful to the project art direction.
- Identity, proportions, composition, visual mass, and baseline are preserved.
- Detail has been consolidated intentionally instead of blurred or stripped of defining elements.

Present the static comparison to the user and wait for approval. After approval, apply the same optical-correction rules to related identity sources and key poses. After rejection, revise only the cited problems in the static frame.

Completion criteria: the user explicitly selects one static target frame and confirms how the correction rules apply across the related action frames.
