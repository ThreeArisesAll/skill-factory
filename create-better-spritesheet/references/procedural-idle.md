# Deterministic Planted Idle Recipe

Use only for a subtle breathing idle that is front-facing, full-body, planted at the soles, and rendered in square frames. For other actions and cameras, use the general motion workflow in [motion-design.md](motion-design.md) and a production method suited to the action.

## Motion chain

- Let the head and shoulders carry the primary rise and fall.
- Connect the upper and lower body through smaller torso and hip motion.
- Reduce participation progressively through the knees and shoe uppers.
- Lock only the sole contact band and foot baseline.
- Control horizontal center-of-mass drift.

Prefer the project's frame count, rhythm, amplitude, and action reference. When they are missing, ask the user and request an idle reference. If the user cannot provide one, search Pinterest according to [reference-search.md](reference-search.md) and use the built-in walk reference only as a clarity benchmark. Only after the search yields no usable result and the user explicitly authorizes independent design may you use the following clearly disclosed provisional assumptions: `12` frames including a repeated closing frame, a `500 ms` loop, and peak travel of approximately `3%` of frame height.

## Build

The master must use an exact square working canvas:

```bash
<python> <skill-dir>/scripts/build_idle_spritesheet.py \
  --master <absolute-transparent-mother-frame> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-idle> \
  --frame-size <contract-frame-size> \
  --frame-count <contract-frame-count> \
  --working-scale <working-scale-at-least-4> \
  --margin <contract-safe-margin> \
  --amplitude <contract-peak-travel> \
  --loop-duration-ms <contract-loop-duration>
```

Use `--fit-master` for a single normalization pass only. The script deterministically derives every frame from the same master, deforms in premultiplied Alpha, downsamples only once at the end, and emits individual frames, a horizontal spritesheet, and a lossless preview.

## Validate

```bash
<python> <skill-dir>/scripts/validate_spritesheet.py \
  --sheet <absolute-idle-sheet.png> \
  --frame-size <contract-frame-size> \
  --frame-count <contract-frame-count> \
  --profile idle-planted \
  --require-closed-loop
```

Override safe-margin, travel, center-of-mass, or contact-band thresholds from the live contract. Watch at least three consecutive loops. Reject piston-like upper-body motion, a frozen lower body, sole sliding, identity drift, and a visible jump at the loop boundary.

Completion criteria: specialized mechanical checks pass, force transfers naturally at native size, and sole contact and loop closure match the idle contract.
