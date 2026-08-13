# Runtime Integration Contract

Use this workflow only when the user explicitly requests replacement or integration of runtime assets. Record that authority under [approval-protocol.md](approval-protocol.md).

## Inspect the live system first

Use repository search, asset manifests, build configuration, and tests to read and record:

- Production path, dimensions, grid, directions, states, and integrity fields for the target asset
- Spritesheet declarations, action-direction clip mappings, frame order, per-frame durations, and loop behavior
- State-to-animation mappings and fallback logic
- Event frames and hotspots for hits, releases, landings, and interaction completion
- Origin, anchor, pivot, root motion, scale, baseline, cropping, and texture registration
- Filtering and pixel-alignment settings in the engine, Canvas, WebGL, or CSS
- Asset validation commands, visual tests, and real rendering entry points

Do not assume a repository uses a fixed directory, filename, engine, or test command. Locate the live contract through `rg`, configuration files, and package scripts before deciding whether the new sheet is compatible. A single-action review strip is not necessarily a production-ready full sheet.

## Update atomically

When integration is authorized, update every genuinely interdependent item together:

1. Production image assets
2. Asset dimensions, grid, layout, and integrity declarations
3. Clips, states, directions, frame counts, per-frame durations, loops, and transitions
4. Anchors, roots, baselines, event frames, display scale, and cropping
5. Loading, caching, or texture registration
6. Test fixtures and assertions governed by the same contract

Keep the new asset consistent with neighboring characters or states in visual mass, contact principles, and gameplay readability. Prefer shared contract updates. Use character-specific compensation only when the design genuinely requires it.

## Match the production profile

The package builder currently implements the `smooth-raster/v1` profile defined in [quality-contract.md](quality-contract.md). Integrate its output with linear interpolation, antialiasing, and non-integer positions when the live project permits them. Read the current engine and project rules before choosing settings; do not treat one engine's option names as a universal contract.

For example, a Phaser configuration for smooth raster art may include:

```ts
pixelArt: false,
antialias: true,
roundPixels: false,
```

CSS generally uses `image-rendering: auto` for `smooth-raster/v1` presentation. Pixel art requires a separate profile with nearest-neighbor sampling, integer scaling, pixel alignment, and its own executable verification; do not integrate a `smooth-raster/v1` package by switching only the runtime filter. Inspect both test galleries and production entry points so a preview with incorrect filtering is not mistaken for an asset defect.

## Validate

Run the repository-defined asset validation, type or static checks, relevant unit tests, and visual E2E. Select an isolated port and the project-provided `baseURL`; leave unrelated services untouched.

Inspect the project-supported real viewport, camera, and device for:

- Direction, visual mass, anchors, and contacts
- Foreground and background occlusion and camera scaling
- Loops, one-shots, terminal holds, state changes, and fallbacks
- Synchronization of hits, releases, contacts, landings, and other events
- Filtering, transparent edges, and cropping
- Consistency with neighboring characters and scenes

Distinguish automated passes, conditional skips, and visual judgments that still require human confirmation. Record externally produced real-entry-point evidence as `runtime-playback-proof/v1` with classification `SUPPLIED`. The delivery verifier checks its bindings and recorded checks; it does not claim to have observed the runtime. See [production-delivery.md](production-delivery.md).
