# Art Direction Contract

Use one approved identity contract across every canonical view, action, and direction. Convert artistic intent into observable invariants; do not treat a style label as sufficient production guidance.

## Paradigm boundary

Identify the authoring paradigm before applying quality rules:

| Paradigm | Source behavior | Target sampling | Typical review focus |
| --- | --- | --- | --- |
| Smooth raster animation | High-resolution RGBA with antialiasing and partial Alpha | One premultiplied-Alpha downsample | Silhouette, edge color, optical hierarchy, temporal stability |
| Hand-painted reduced raster | Painted source designed for reduction | Profile-specific filtering and sharpening | Form grouping, texture survival, edge hierarchy |
| Pixel art | Pixel-grid-native shapes and palette decisions | Nearest-neighbor integer scaling | Clusters, stair steps, palette ramps, pixel timing |

Never mix pixel-art requirements such as integer cluster construction with smooth-raster outline or resampling rules. The installed create/rebuild adapter implements only `smooth-raster/v2`.

## Identity contract

Record these fields in `identity-bible/v2` before motion-source authoring:

- Subject and concise art direction
- One canonical view per required direction-camera pair
- Proportion and optical-size rules
- Palette and value-group rules
- Material response rules
- Lighting and cast-shadow rules
- Recognition constraints
- Allowed variations and forbidden drift
- Equipment ID, body side, and invariants

Use stable, observable statements. Prefer “satchel remains on character-left and crosses behind the torso on west-facing views” over “keep accessories consistent.” A canonical view is authoritative only for its declared direction and camera.

## Cross-frame visual review

Review every planned source and final target cell for:

- Character identity, body proportions, head-to-body ratio, limb length, costume construction, equipment side, and distinctive recognition shapes
- Palette families, local color, material separation, highlight size, light direction, cast-shadow direction, and ambient contrast
- Silhouette readability, negative-space openings, visual mass, center, baseline, and comparable occupied size
- Projection, foreshortening, near-far limb ordering, occlusion, and surfaces newly revealed by rotation
- Consistent outline hierarchy and target-size edge behavior under the active profile

Measure bounds, margins, Alpha area, and centroids as supporting evidence. These measurements can reveal drift; they cannot decide anatomy, appeal, material identity, or whether a pose communicates the intended action.

## Direction sets

Bind every clip to a declared canonical direction-camera view. For mirrored or multi-direction sets, inspect rather than assume:

- Screen-space travel and action intent
- Near and far limbs
- Equipment handedness and body side
- Asymmetric costume elements
- Weapon grip, attack side, and effect origin
- Volume, horizon, and camera elevation

Reject a direction-camera mismatch before creating a job. When a new view exposes previously unseen surfaces, require those surfaces to be described in the complete motion plan and reviewed for identity continuity.

## Native-size acceptance

Inspect target cells at native `1x` on a neutral background. Enlarged views help locate defects but cannot replace native-size judgment. Confirm that recognition anchors, pose silhouette, contacts, equipment, and event readability survive reduction without clogged gaps or competing microdetail.

When native-size readability fails, correct the owning high-resolution canonical or raw action source. Consolidate detail, strengthen large-form separation, or revise Alpha while preserving the approved identity. Never paint corrections into a target cell or assembled sheet.
