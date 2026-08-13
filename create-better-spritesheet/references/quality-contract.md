# Spritesheet Quality Contract v4

## Production contract

Resolve material values from user input and authoritative repository evidence. Ask at most three material questions per round and only for missing, ambiguous, or conflicting values; apply assumptions only after explicit delegation.

Resolve character, identity evidence, art direction, actions, action topology, directions, camera, transitions, playback, root motion, coordinate contract, target geometry, timing, events, grid, runtime scale, visual treatment, sampling, outline, review scope, and integration scope. Execute consistent outline `enabled` and `target_width` values without reconfirmation; use `none` when disabled.

Keep working-plan values outside `spritesheet-production-request/v4` when the executable schema does not encode them. Record job and delivery evidence through [production-delivery.md](production-delivery.md), not as additions to the closed pixel-package manifest.

Require a target shortest side below `512 px`, a target longest side at most `4096 px`, and a derived high-resolution longest side at most `16384 px`.

Complete the production contract when every material decision is authoritative, approved under [approval-protocol.md](approval-protocol.md), or explicitly delegated and the package subset can be serialized as `spritesheet-production-request/v4`.

## Production profiles

The installed executable production profile is `smooth-raster/v1`:

- Author RGBA sources at high resolution with smooth antialiasing.
- Treat the finalized source Alpha as the pose silhouette.
- Follow the deterministic pixel derivation owned by [lineage-evidence.md](lineage-evidence.md).
- Use smooth runtime filtering and permit non-integer presentation when project rules support it.

Pixel art is an independent profile with different authoring, quantization, outline, sampling, alignment, and runtime constraints. Create and rebuild requests for pixel art must return typed `UNSUPPORTED_CAPABILITY` because no production adapter is installed. Diagnose and review supplied pixel-art artifacts read-only without silently converting profiles or claiming `smooth-raster/v1` verification.

Infer the profile from authoritative assets, renderer settings, and repository rules. Ask only when the evidence is absent or conflicting and the choice changes production.

## Visual quality gates

Review canonical references for identity, anatomy, palette, equipment, direction, camera, visual mass, transparency, and native-size outline aesthetics.

Review raw high-resolution sources for identity, volume, body planes, projection, foreshortening, overlap, depth, contacts, arcs, mask correctness, outline suitability, and sufficient safe margin. Finish every Alpha-changing operation before byte-bound review.

Review the rendered sequence for topology, spacing, timing, transitions, events, native-size recognition, temporal flicker, transparent edges, clipping, loop seams, and terminal holds. Use the [approval protocol](approval-protocol.md) for every gate and [lineage-evidence.md](lineage-evidence.md) for package proof semantics.

## Correction ownership

| Symptom | Owning stage | Required consequence |
| --- | --- | --- |
| Identity, palette, neutral direction, camera, or art direction is wrong | Identity bible and canonical authoring | Prepare, admit, and approve new canonical bytes; invalidate dependent motion and delivery evidence |
| Canonical admission evidence or replay mismatches | Canonical preparation | Regenerate complete evidence; admit no canonical until replay passes |
| Topology, pose, perspective, volume, occlusion, spacing, timing, contact, or transition is wrong | Motion blueprint, keyframes, or sequence authoring | Correct the earliest owning motion input and repeat dependent approvals |
| Alpha, transparency, background edge, detached noise, crop, or source optical treatment is wrong | Raw frame-source authoring | Correct authoritative source bytes; repeat bound reviews and rebuild |
| Ring pixels, outline thickness or color, safe margin, sampling, or assembly is wrong | Outline contract or deterministic renderer | Correct the contract or renderer; regenerate receipt, manifest, sheet, and delivery binding |
| Order, duration, event, anchor, or other runtime metadata is wrong | Production contract and metadata projection | Regenerate manifest or runtime projection at the owning layer |
| Live filtering, scaling, event playback, or state transition is wrong | Runtime integration | Correct integration and regenerate runtime-playback proof |

Terminate source corrections at approved raw bytes, rendering corrections at a replayable batch receipt, metadata corrections at an internally consistent projection, and runtime corrections at current playback evidence. Keep target cells and the assembled sheet immutable outputs.
