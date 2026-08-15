---
name: video-to-spritesheet
description: Extract one verified, loopable transparent character animation and spritesheet from a local MP4, MOV, WebM, or MKV with a solid or near-solid background. Use when the source video is the sole pose and motion authority and the result must preserve timing, aspect ratio, transparency, outline order, and deterministic lineage. Do not use for inventing frames, multi-action splitting, complex moving backgrounds, or character repainting.
---

# Video to Spritesheet

Produce a deterministic transparent animation from one local video without generating character content. Treat every quality failure as evidence requiring diagnosis, not permission to bypass a gate.

## Preconditions

Require all of the following:

- One local MP4, MOV, WebM, or MKV
- One character performing one loopable action
- A solid or near-solid background
- A requested final short edge divisible by four and within 4 to 512 pixels

Reject complex scenes, multiple video streams without an explicit selection, ambiguous cycles, missing complete cycles, and requests for interpolation, in-betweening, repainting, cropping, stretching, or repositioning.

Read [references/contracts.md](references/contracts.md) before running the pipeline. Read [references/quality-gates.md](references/quality-gates.md) when interpreting failures or reporting acceptance.

## Workflow

1. Inspect the video before writing output:

   ```bash
   python3 scripts/video_to_spritesheet.py inspect --input /absolute/path/input.mp4
   ```

2. Review duration, frame timing, display rotation, background explainability, and ranked cycle candidates. If cycle selection is ambiguous, report the typed failure. Use explicit cycle times only when the user or visible evidence establishes the intended interval; explicit bounds never bypass quality gates.

3. Run the full pipeline into a new directory:

   ```bash
   python3 scripts/video_to_spritesheet.py run \
     --input /absolute/path/input.mp4 \
     --output /absolute/path/output \
     --target-short-edge 128
   ```

4. Verify the finished output independently:

   ```bash
   python3 scripts/video_to_spritesheet.py verify --output /absolute/path/output
   ```

5. Inspect `inspection/overview.png`, `inspection/loop-seam.png`, and the transparent APNG. Machine verification does not establish human visual acceptance. Report that distinction explicitly.

## Run options

- Repeat `--background '#RRGGBB'` for one or more explicit background colors; omit it or use `--background auto` for estimation.
- Use `--cycle-start SECONDS --cycle-end SECONDS` together for an explicit inclusive interval.
- Use `--sheet-columns N`; the default is four. Unused cells remain RGBA zero.
- Use `--outline-color auto` to estimate one shared color from the character's existing outer contour.
- Use `--dry-run` to validate the media and parameters without creating output.
- Use `--resume` only for an already complete job with the exact same input hash and parameters.

The pipeline normalizes the working short edge to 512 pixels without cropping, applies the outward outline at working resolution, then performs one floating-point premultiplied-alpha Lanczos resize. Never re-outline final frames or the sheet.

## Failure handling

The command writes structured JSON errors to stderr and returns nonzero. Do not add force flags, overwrite output, silently accept warnings, or manually edit deliverables after verification. Use:

```bash
python3 scripts/video_to_spritesheet.py diagnose --output /absolute/path/output
```

Create a fresh output directory after changing parameters. Preserve the failed directory when it contains useful diagnostics.

## Delivery

Deliver `job.json`, `quality-report.json`, final frames, `spritesheet.png`, `loop-preview.png`, and inspection images. State:

- The input and selected cycle
- Working and final geometry
- Frame count and timing behavior
- Synthetic and real-animation gate results
- Machine verification status
- Human visual review status
- Every failure or unresolved limitation
