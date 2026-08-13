# Spritesheet Quality Contract v4

## Production spec

Resolve material values from user input and authoritative repository evidence. Ask only for missing, ambiguous, or conflicting values; apply assumptions only after explicit delegation.

Keep identity evidence, art direction, fallback policy, runtime scale, hotspot geometry, review scope, and integration scope in the working plan when the closed `spritesheet-production-request/v4` does not encode them. Serialize only fields accepted by the CLI.

Resolve character, actions, directions, camera, transitions, playback, root motion, coordinate contract, target geometry, timing, events, grid, visual treatment, sampling, and outline. Execute consistent outline `enabled` and `target_width` values without reconfirmation; use `none` when disabled.

Require a target shortest side below `512 px`, a target longest side at most `4096 px`, and a derived high-resolution longest side at most `16384 px`.

## Canonical boundary

Canonical preparation remains `canonical-authoring-request/v3`, `canonical-reference-evidence/v3`, and `canonical-admission-proof/v1`. Replay canonical normalization and its outline or identity derivation before canonical review. Bind `canonical-approval` to the exact candidate and proof hashes.

Use the canonical as identity, art-direction, camera, and direction evidence. Treat generator use and obedience as declared creative relationships. A newly generated pose has a new silhouette, so canonical admission proves neither that pose's Alpha nor its formal outline.

Review the canonical for identity, anatomy, palette, equipment, direction, camera, mass, transparency, and outline aesthetics. Reuse it only with a full current admission match.

## Complete frame-description gate

Before any keyframe generation, require the user to approve the latest complete ordered frame-description plan defined in [motion-design.md](motion-design.md). Apply the gate to every playback position in the current batch. A modification invalidates the prior plan approval and requires the entire revised plan to be presented and explicitly approved again before image generation resumes.

Treat frame descriptions as `DECLARED` intent and the explicit user decision as `REVIEWED`. Keep both outside the closed production request and package schemas. Do not use this gate to reconfirm resolved outline settings.

## Raw high-resolution source gates

Generate raw keyframe sources anew from the current user-approved complete frame-description plan, using the applicable canonical and action evidence. Complete background removal, Alpha cleanup, crop placement, canvas normalization, and optical correction before keyframe approval. The resulting Alpha is the authoritative pose silhouette.

Bind `keyframe-set-approval` to the canonical admission proof and complete ordered raw keyframe-source bytes. Generate raw in-between sources using the same canonical plus adjacent approved keyframes, complete every Alpha-changing operation, and bind `sequence-approval` to the same proof and complete ordered raw sequence bytes.

Review identity, volume, body planes, projection, foreshortening, overlap, depth, contacts, arcs, timing, transitions, mask correctness, outline suitability, and aesthetics. Record these as `REVIEWED`. Record canonical use or obedience as `DECLARED`. Require no per-frame admission object.

## Deterministic rendering and package acceptance

Run `build-package` with `spritesheet-production-request/v4`. For each unique approved raw source, use its final Alpha as authoritative, derive the resolved silhouette outline in memory or apply the declared identity operation when disabled, and resize the resulting buffer exactly once with `lanczos-premultiplied-v1` into its target cell. Store straight RGBA and clear RGB beneath zero Alpha.

Treat the outlined high-resolution buffer as ephemeral and the target cell as a sheet region. Apply no outline operation after target resizing. Reuse opening target-cell pixels only for an explicit loop-closing alias.

Embed one `spritesheet-rendering-receipt/v1` object in the v4 manifest's top-level `rendering` field. Require `verify-package` to replay canonical admission and the complete raw-source-to-sheet rendering equation, then compare the final sheet exactly. Treat schemas, hashes, dimensions, topology, outline derivation, sampling, assembly, closure, and replayed pixels as `MACHINE-VERIFIED`.

Deliver one `SpritesheetPackage`: the fixed-grid spritesheet, one authoritative v4 manifest, its referenced content-addressed raw sources, and canonical admission material required for replay.

## Correction routing

| Symptom | Return to | Required consequence |
| --- | --- | --- |
| Canonical identity, palette, direction, camera, or art direction is wrong | Canonical authoring | Prepare, admit, and approve new canonical bytes; invalidate dependent reviews and package outputs |
| Canonical admission evidence or replay mismatches | Canonical preparation | Regenerate complete evidence; admit no canonical until replay passes |
| Pose, perspective, volume, occlusion, timing, contact, or transition is wrong | Raw keyframe or sequence generation | Correct raw sources and repeat affected reviews before rebuilding |
| Pose Alpha, transparency, background edge, detached noise, crop, or optical source treatment is wrong | Raw frame-source authoring | Correct the authoritative source bytes; repeat bound reviews and rebuild |
| Ring pixels, outline thickness or color, safe margin, sampling, or assembly is wrong | Outline contract or deterministic renderer | Correct the contract or renderer; regenerate receipt, manifest, and sheet |
| Order, duration, event, anchor, or other runtime metadata is wrong | Production spec and package build | Regenerate manifest and sheet together |

Terminate source corrections at approved raw bytes and rendering corrections at a replayable batch receipt. Keep target cells and the assembled sheet immutable outputs.
