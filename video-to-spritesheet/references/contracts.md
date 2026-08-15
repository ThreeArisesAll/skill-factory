# Contracts

## Capability boundary

Accept one local MP4, MOV, WebM, or MKV containing one character performing one loopable action against a solid or near-solid background. Preserve decoded source poses. Permit deterministic decoding, cycle selection, scaling, cutout, edge decontamination, authorized background-only watermark removal, outward outlining, premultiplied-alpha resizing, and assembly. Return a typed failure when the request requires scene segmentation, pose invention, in-between generation, content repainting, or multi-action splitting.

After cutout, preserve the dominant connected character region and components within 12 working pixels of it. Remove only remote components no larger than 0.25 percent of the dominant component, treating them as detached capture artifacts. Fail instead of guessing when a remote component exceeds that limit. This rule must never be used to remove a component near the character.

When a source has strongly varying near-solid backgrounds, perform cutout and edge decontamination in each original frame's background color space. Never manufacture a stable-background derivative by filling a silhouette mask and then treat that derivative as the matte authority: enclosed pockets and antialiased edges retain the original background colors. A stable-background derivative is admissible only after the original-background matte and decontamination are complete, and every original background family that remains possible at the edge must be declared to the formal run.

Default to edge-connected background admission so foreground colors close to the background remain protected. Permit global background admission only after visual evidence establishes that the subject palette does not overlap any declared background color. Global mode clears pixels inside the declared tolerance anywhere on the canvas and must remain an explicit recorded parameter.

## Watermarks

- Analyze every decoded frame and report remote foreground candidates in display-pixel coordinates before cycle extraction.
- Treat candidate detection as machine evidence requiring visual classification; it cannot distinguish every watermark from an intentional detached prop.
- Reject detected candidates by default.
- Require the caller's explicit authorization claim and one or more visually reviewed regions before removal.
- Constrain repair to reviewed background regions. Use background-constrained inpainting away from the canvas edge and a subject-free same-frame donor patch for an edge-touching region. Reject a region that intersects the dominant subject, exceeds the frame, lacks a safe donor when one is required, or contains no removable foreground.
- Re-run the same detector on every selected frame after removal and require the reviewed regions to be `clear` before cutout. Preserve candidates outside the reviewed regions as diagnostics; they can be intentional detached content and must not be silently removed or mislabeled as repaired watermark residue.
- Preserve the input file. Store repaired selected-source frames, removal diagnostics, reviewed regions, authorization class, and hashes in the output closure.
- Keep watermark background tolerance independent from character matte tolerance when source variation requires a broad review model and a tighter decontaminated cutout.

## Geometry

- Apply display rotation before analysis.
- Preserve the source aspect ratio and one shared transform for the entire selected cycle.
- Set the working short edge to 512 pixels.
- Require `target-short-edge` in `[4, 512]` and divisible by four.
- Round the corresponding long edge from the source display ratio.
- Keep non-square canvases. Do not crop, stretch, or reposition the subject.
- Apply the outline at working resolution, then resize once with floating-point premultiplied-alpha Lanczos. Never re-outline final frames.
- When the animation must match an existing production set, require a production spritesheet or frame as `--outline-reference`. Estimate its external contour color independently and fail when the selected shared outline color exceeds the declared perceptual-distance limit.

## Output closure

The output directory contains `job.json`, analysis records, selected source frames, high-resolution cutouts, high-resolution outlined frames, final frames, `spritesheet.png`, `loop-preview.png`, `quality-report.json`, and inspection images. `job.json` uses relative paths and excludes timestamps, UUIDs, and absolute output paths. Hash every deliverable except the manifest itself.

## Claim classes

- `MACHINE-VERIFIED`: recomputed from files by the verifier.
- `HUMAN-REVIEWED`: explicitly inspected by a person.
- `SUPPLIED`: asserted by the caller or container metadata.
- `UNRESOLVED`: not established by available evidence.

Machine success never implies human visual acceptance.

## Stable failure codes

`UNSUPPORTED_INPUT`, `UNSUPPORTED_BACKGROUND`, `AMBIGUOUS_VIDEO_STREAM`, `NO_COMPLETE_CYCLE`, `AMBIGUOUS_CYCLE`, `BACKGROUND_ESTIMATION_FAILED`, `WATERMARK_REVIEW_FAILED`, `WATERMARK_DETECTED`, `WATERMARK_AUTHORIZATION_REQUIRED`, `WATERMARK_REGION_REQUIRED`, `WATERMARK_REGION_INVALID`, `WATERMARK_OVERLAPS_SUBJECT`, `WATERMARK_NOT_FOUND`, `WATERMARK_REMOVAL_FAILED`, `CUTOUT_QUALITY_FAILED`, `OUTLINE_COLOR_UNCERTAIN`, `OUTLINE_COLOR_MISMATCH`, `OUTLINE_CLIPPED`, `TEMPORAL_QUALITY_FAILED`, `OUTPUT_VERIFICATION_FAILED`, and `DEPENDENCY_MISSING`.
