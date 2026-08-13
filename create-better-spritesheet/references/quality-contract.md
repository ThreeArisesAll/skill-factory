# Spritesheet Quality Contract v3

## Production spec

Resolve material values from user input and authoritative repository evidence. Ask only for missing, ambiguous, or conflicting values; apply assumptions only after explicit delegation.

Keep identity evidence, art direction, fallback policy, runtime scale, hotspot geometry, review scope, and integration scope in the working plan when the closed `spritesheet-production-request/v3` does not encode them. Serialize only fields accepted by the CLI.

Resolve character, actions, directions, camera, transitions, playback, root motion, coordinate contract, target geometry, timing, events, grid, visual treatment, sampling, and outline. Execute consistent outline `enabled` and `target_width` values without reconfirmation; use `none` when disabled.

Require a target shortest side below `512 px`, a target longest side at most `4096 px`, and a derived high-resolution longest side at most `16384 px`.

## Canonical admission and approval

Treat canonical preparation as a deterministic admission boundary. Normalize the content-addressed original authoring source in memory and apply the resolved outward outline when enabled. Require `prepare-canonical` to emit the candidate, evidence, `canonical-admission-proof/v1`, and content-addressed source evidence only after replay passes. Keep the normalized buffer ephemeral. Follow [silhouette-outline.md](silhouette-outline.md) for the proof boundary.

After machine proof exists, use visual review to judge identity, anatomy, silhouette quality, palette, equipment, direction, camera, mass, coordinate semantics, transparency, and outline aesthetics. Do not use visual linework or human review to establish execution history. Bind `canonical-approval` to both admitted candidate bytes and the admission-proof hash.

Reuse an approved canonical only with a full current admission match. Any bound source, target, algorithm, outline, or candidate change requires new admission, approval, and downstream production.

## High-resolution frame gates

Use only `high-resolution-frame` with role `keyframe` or `in-between` for action sources. Generate keyframes anew from the applicable admitted canonical and action evidence. Bind `keyframe-set-approval` to the canonical admission proof and complete ordered keyframe set.

Generate in-betweens anew from the same admitted canonical plus adjacent approved keyframes. Add and reapprove a keyframe when an interval does not constrain articulation, projection, visible surfaces, or occlusion. Bind `sequence-approval` to the same admission proof and complete ordered sequence.

Use new image generation rather than deformation as the production method. Review volume, body planes, projection, foreshortening, overlap, depth, contacts, arcs, timing, events, and transitions as aesthetic and motion judgments.

## Sampling and package acceptance

Render each logical cell directly from its approved high-resolution source with `lanczos-premultiplied-v1`. Store straight RGBA and clear RGB beneath zero Alpha. Treat cells as regions of the sheet, not artifacts. Reuse opening pixels only for an explicit loop-closing alias.

Require `build-package` and `verify-package` to consume the packaged canonical admission evidence and replay its normalization and outline derivation. Require verification to replay every target-cell sample and compare pixels exactly. Treat deterministic replay, schema closure, hashes, dimensions, topology, coverage, and metadata consistency as machine facts. Treat identity, aesthetics, motion quality, and reviewer intent as human judgments.

Deliver one `SpritesheetPackage`: the fixed-grid spritesheet, one authoritative `spritesheet-package/v3` `manifest.json`, and its referenced content-addressed production sources and admission material.

## Correction routing

| Symptom | Return to | Required consequence |
| --- | --- | --- |
| Identity, palette, transparency, optical design, or outline is wrong | Canonical authoring | Prepare, admit, and approve new canonical bytes; invalidate all dependents |
| Admission evidence or replay mismatches | Canonical preparation | Regenerate complete evidence; admit no canonical until replay passes |
| Pose, perspective, volume, occlusion, timing, contact, or event is wrong | Keyframe or sequence generation | Repeat affected gates before rebuilding |
| Native cell sampling fails | Responsible high-resolution source | Correct and reapprove the source, then rebuild |
| Order, range, duration, event, or anchor metadata is wrong | Production spec and package build | Regenerate manifest and sheet together |

Terminate corrections at an admitted and approved source. Never patch a sheet cell.
