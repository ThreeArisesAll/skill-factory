# Deterministic Planted Idle Recipe

Use only for a subtle breathing idle that is front-facing, full-body, planted at the soles, and rendered in square frames. For other actions and cameras, use the general motion workflow in [motion-design.md](motion-design.md) and a production method suited to the action.

## Motion chain

- Let the head and shoulders carry the primary rise and fall.
- Connect the upper and lower body through smaller torso and hip motion.
- Reduce participation progressively through the knees and shoe uppers.
- Lock only the sole contact band and foot baseline.
- Control horizontal center-of-mass drift.

Prefer the project's frame count, rhythm, amplitude, and action reference. When they are missing, ask the user and request an idle reference unless the user explicitly says no action reference is needed. Treat that opt-out as authorization to design from written intent and present the provisional motion contract for approval. If the user cannot provide a reference but has not declined references, search Pinterest according to [reference-search.md](reference-search.md) and use the built-in walk reference only as a clarity benchmark. Only after explicit opt-out or a search with no usable result may you propose the following clearly disclosed assumptions: `12` frames including a repeated closing frame, a `500 ms` loop, and peak travel of approximately `3%` of frame height.

## Build

The canonical master must use an exact `512×512` square canvas:

```bash
<python> <skill-dir>/scripts/build_idle_spritesheet.py \
  --master <absolute-transparent-mother-frame> \
  --output-dir <absolute-fresh-output-directory> \
  --name <character-idle> \
  --frame-size <contract-frame-size> \
  --frame-count <contract-frame-count> \
  --margin <contract-safe-margin> \
  --amplitude <contract-peak-travel> \
  --loop-duration-ms <contract-loop-duration>
```

Pass a locked canonical master whose outline treatment is already complete. When the outline contract is enabled, normalize the pre-master and run the silhouette-outline workflow before invoking this script, then pass the outlined canonical master without `--fit-master`. Use `--fit-master` for a single normalization pass only when the outline contract is disabled. The script deterministically derives every frame from the same master, deforms in premultiplied Alpha, downsamples only once at the end, and emits individual frames, a horizontal spritesheet, and a lossless preview.

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
