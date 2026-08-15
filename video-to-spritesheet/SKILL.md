---
name: video-to-spritesheet
description: Inspect one local MP4, MOV, WebM, or MKV for watermarks and extract a verified, loopable transparent character animation and spritesheet from a solid or near-solid background. Use when the source video is the sole pose and motion authority and the result must preserve timing, aspect ratio, transparency, outline order, authorized background-only watermark removal, and deterministic lineage. Do not use for inventing frames, multi-action splitting, complex moving backgrounds, or character repainting.
---

# Video to Spritesheet

Produce a deterministic transparent animation from one local video without generating character content. Treat every quality failure as evidence requiring diagnosis, not permission to bypass a gate.

## Preconditions

Require all of the following:

- One local MP4, MOV, WebM, or MKV
- One character performing one loopable action
- A solid or near-solid background
- A requested final short edge divisible by four and within 4 to 512 pixels
- Explicit confirmation that the caller is authorized before any watermark removal

Reject complex scenes, multiple video streams without an explicit selection, ambiguous cycles, missing complete cycles, and requests for interpolation, in-betweening, repainting, cropping, stretching, or repositioning.

Read [references/contracts.md](references/contracts.md) before running the pipeline. Read [references/quality-gates.md](references/quality-gates.md) when interpreting failures or reporting acceptance.

## Workflow

1. Inspect the video before writing output:

   ```bash
   python3 scripts/video_to_spritesheet.py inspect --input /absolute/path/input.mp4
   ```

2. Review duration, frame timing, display rotation, background explainability, ranked cycle candidates, and `watermark_review`. The scanner analyzes every decoded frame and reports detached foreground candidates in display-pixel coordinates. Treat `clear` as machine evidence only and visually inspect the source. Treat `detected` as a review request because an intentional detached prop can resemble a watermark. Stop on `ambiguous`. If the near-solid background changes strongly, keep the original decoded frames as matte authority: cut out and decontaminate against each frame's original background before any stable-background composite.

3. If review confirms the input is clear, run the full pipeline into a new directory. The default `reject` action stops if a candidate is detected:

   ```bash
   python3 scripts/video_to_spritesheet.py run \
     --input /absolute/path/input.mp4 \
     --output /absolute/path/output \
     --target-short-edge 128
   ```

4. If the user confirms authorization and visually approves a candidate region, repeat `--watermark-region X,Y,WIDTH,HEIGHT` as needed and run:

   ```bash
   python3 scripts/video_to_spritesheet.py run \
     --input /absolute/path/input.mp4 \
     --output /absolute/path/output \
     --target-short-edge 128 \
     --outline-reference /absolute/path/production-reference.png \
     --watermark-action remove \
     --watermark-region 633,671,87,44 \
     --watermark-removal-authorized
   ```

   Use display-pixel coordinates from the reviewed inspection. The pipeline constrains repair to each reviewed background region, uses inpainting away from the canvas edge and a subject-free same-frame background donor at the edge, rejects any region that overlaps the dominant subject, writes cleaned selected-source frames without overwriting the input video, and requires every reviewed region to be clear in the post-removal scan. Candidates outside reviewed regions remain diagnostics rather than being deleted as presumed watermarks.

5. Verify the finished output independently:

   ```bash
   python3 scripts/video_to_spritesheet.py verify --output /absolute/path/output
   ```

6. Inspect `analysis/watermark.json`, `inspection/overview.png`, `inspection/loop-seam.png`, and the transparent APNG. Check the repaired background across the full loop when removal occurred. Machine verification does not establish human visual acceptance. Report that distinction explicitly.

## Run options

- Repeat `--background '#RRGGBB'` for one or more explicit background colors; omit it or use `--background auto` for estimation.
- Keep `--background-mode edge-connected` unless visual review establishes that the character palette does not overlap any admitted background color. In that proven case, use `--background-mode global` to clear admitted background colors from enclosed gaps as well as the exterior; never use it to force a result when palette overlap is uncertain.
- Use `--watermark-background-tolerance N` when the broad tolerance needed for watermark review differs from the tighter original-background matte tolerance. It affects only watermark analysis and repair, never the character cutout.
- Use `--cycle-start SECONDS --cycle-end SECONDS` together for an explicit inclusive interval.
- Use `--sheet-columns N`; the default is four. Unused cells remain RGBA zero.
- Use `--outline-color auto` to estimate one shared color from the character's existing outer contour.
- Use `--outline-reference /absolute/path/reference.png` whenever the result must match an existing production set. The run independently estimates the reference's external contour color and fails if the selected color differs by more than `--outline-reference-max-distance` (default 6.0 in Lab space).
- Use `--watermark-action reject` by default. Use `remove` only with one or more reviewed `--watermark-region X,Y,WIDTH,HEIGHT` values and `--watermark-removal-authorized`.
- Use `--dry-run` to validate the media and parameters without creating output.
- Use `--resume` only for an already complete job with the exact same input hash and parameters.

The pipeline normalizes the working short edge to 512 pixels without cropping, applies the outward outline at working resolution, then performs one floating-point premultiplied-alpha Lanczos resize. Never re-outline final frames or the sheet. The real-animation gate also rejects excessive background-like color along the outer contour; do not bypass it by omitting known source-background colors.

## Failure handling

The command writes structured JSON errors to stderr and returns nonzero. Do not add force flags, overwrite output, silently accept warnings, or manually edit deliverables after verification. Use:

```bash
python3 scripts/video_to_spritesheet.py diagnose --output /absolute/path/output
```

Create a fresh output directory after changing parameters. Preserve the failed directory when it contains useful diagnostics.

## Delivery

Deliver `job.json`, `quality-report.json`, `analysis/watermark.json`, cleaned selected-source frames when applicable, final frames, `spritesheet.png`, `loop-preview.png`, and inspection images. State:

- The input and selected cycle
- Working and final geometry
- Frame count and timing behavior
- Watermark pre-scan status, authorization claim, reviewed regions, removal method, and post-scan status
- Synthetic and real-animation gate results
- Machine verification status
- Human visual review status
- Every failure or unresolved limitation
