# Contracts

## Capability boundary

Accept one local MP4, MOV, WebM, or MKV containing one character performing one loopable action against a solid or near-solid background. Preserve decoded source poses. Permit deterministic decoding, cycle selection, scaling, cutout, edge decontamination, outward outlining, premultiplied-alpha resizing, and assembly. Return a typed failure when the request requires scene segmentation, pose invention, in-between generation, content repainting, or multi-action splitting.

After cutout, preserve the dominant connected character region and components within 12 working pixels of it. Remove only remote components no larger than 0.25 percent of the dominant component, treating them as detached capture artifacts. Fail instead of guessing when a remote component exceeds that limit. This rule must never be used to remove a component near the character.

## Geometry

- Apply display rotation before analysis.
- Preserve the source aspect ratio and one shared transform for the entire selected cycle.
- Set the working short edge to 512 pixels.
- Require `target-short-edge` in `[4, 512]` and divisible by four.
- Round the corresponding long edge from the source display ratio.
- Keep non-square canvases. Do not crop, stretch, or reposition the subject.
- Apply the outline at working resolution, then resize once with floating-point premultiplied-alpha Lanczos. Never re-outline final frames.

## Output closure

The output directory contains `job.json`, analysis records, selected source frames, high-resolution cutouts, high-resolution outlined frames, final frames, `spritesheet.png`, `loop-preview.png`, `quality-report.json`, and inspection images. `job.json` uses relative paths and excludes timestamps, UUIDs, and absolute output paths. Hash every deliverable except the manifest itself.

## Claim classes

- `MACHINE-VERIFIED`: recomputed from files by the verifier.
- `HUMAN-REVIEWED`: explicitly inspected by a person.
- `SUPPLIED`: asserted by the caller or container metadata.
- `UNRESOLVED`: not established by available evidence.

Machine success never implies human visual acceptance.

## Stable failure codes

`UNSUPPORTED_INPUT`, `UNSUPPORTED_BACKGROUND`, `AMBIGUOUS_VIDEO_STREAM`, `NO_COMPLETE_CYCLE`, `AMBIGUOUS_CYCLE`, `BACKGROUND_ESTIMATION_FAILED`, `CUTOUT_QUALITY_FAILED`, `OUTLINE_COLOR_UNCERTAIN`, `OUTLINE_CLIPPED`, `TEMPORAL_QUALITY_FAILED`, `OUTPUT_VERIFICATION_FAILED`, and `DEPENDENCY_MISSING`.
