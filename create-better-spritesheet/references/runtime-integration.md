# Runtime Integration Contract

Use this workflow only when the user explicitly authorizes changes to a target repository or runtime. Current `spritesheet-production-delivery/v2` ends at `package-ready`; runtime replacement is a separate downstream action.

## Inspect the live system

Trace the actual production entry point, asset manifest, loader, renderer, animation state machine, and tests. Record:

- Asset path, integrity fields, dimensions, grid, order, and texture registration
- Clip and direction mapping, durations, loops, terminal holds, transitions, and fallbacks
- Event frames, hit or release timing, and interaction completion
- Origin, anchor, pivot, baseline, root motion, crop, scale, and collision relationships
- Filtering, antialiasing, pixel alignment, camera scaling, and device-pixel behavior
- Repository-defined validation, visual tests, and production rendering path

Do not infer an engine, filename, layout, or filter from the Skill package. A review strip is not automatically a runtime-ready asset.

## Update atomically

When replacement is authorized, update every interdependent item in one reviewable change:

1. Production image and integrity declaration
2. Geometry, grid, order, and texture registration
3. Clip, direction, timing, loop, transition, hold, and event metadata
4. Origin, anchor, baseline, root motion, scale, crop, and collision assumptions
5. Loading, caching, fallback, and state mappings
6. Contract tests, fixtures, and visual acceptance paths

Preserve unrelated work and use repository authority for command and release boundaries.

## Profile-specific presentation

`smooth-raster/v2` expects smooth presentation compatible with antialiased target cells. A Phaser project may use `pixelArt: false`, `antialias: true`, and `roundPixels: false`, but only when live project evidence supports those settings. CSS commonly uses `image-rendering: auto` for smooth raster.

Pixel art requires its own package and runtime contract. Do not integrate a smooth-raster package as pixel art by switching to nearest-neighbor filtering.

## Validate the real entry point

Run repository-defined static checks, asset validation, unit tests, and visual end-to-end coverage. Inspect supported cameras, viewports, and devices for:

- Direction, identity, visual mass, anchors, baseline, contacts, and collisions
- Loop seams, one-shots, holds, transitions, and fallbacks
- Hit, release, contact, landing, and completion events
- Filtering, transparent edges, clipping, scale, and neighboring-character consistency

Report automated results separately from human visual judgment. Runtime files and captures supplied by an external process are `SUPPLIED`; their hashes and bindings may be verified without claiming direct observation. Do not claim `runtime-verified` from a v2 package or delivery alone.
