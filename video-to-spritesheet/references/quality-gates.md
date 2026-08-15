# Quality gates

## Synthetic truth

Run fixed-seed cases covering bright, dark, saturated, low-saturation, noisy, and gently graded backgrounds. Include hard edges, antialiasing, thin structures, concavities, enclosed background pockets, semitransparent edges, and foreground colors close to the background. Measure IoU, precision, recall, F1, alpha MAE, and symmetric boundary error. Calibrate mandatory thresholds from observed baselines and retain a degradation case that must fail.

The 2026-08-15 fixed-seed baseline, measured before freezing the gates, produced worst-case IoU 0.968525, precision 0.983542, recall 0.980954, F1 0.984011, alpha MAE 0.016340, and symmetric boundary error 1.868632 pixels. The mandatory gates retain measurable margin without crossing the observed baseline: IoU at least 0.965, precision at least 0.980, recall at least 0.980, F1 at least 0.980, alpha MAE at most 0.018, and boundary error at most 2.0 pixels. Recalibrate only after an intentional fixture or algorithm revision and preserve the prior measurement in version control.

## Real animation structure

Measure each frame's boundary residue, suspicious transparent holes, retained enclosed background, foreground area, bounding box, partial-alpha width, transparent RGB, and edge contamination. Compare adjacent alpha masks and the last-to-first seam. Detect outliers from median and MAD; report exact frame indices and metrics. These checks establish structural consistency, not pixel-level truth.

Require both a six-scaled-MAD robust outlier and a material difference before rejecting a pair. The measured materiality floors are 0.015 mean alpha difference, 0.040 contour-change ratio, and 0.015 foreground-area change. This prevents sub-percent source-pose changes from being mislabeled as matte instability while preserving rejection of visible jumps. Always include the last-to-first pair in the same gate.

## Visual evidence

Create cycle-candidate, contact-sheet, alpha, edge-detail, black, white, gray, checkerboard, and loop-seam views. Report `human_visual_review: pending` until a person explicitly accepts them.
