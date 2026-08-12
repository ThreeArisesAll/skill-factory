# Lineage Evidence Manifest v1

Use a `spritesheet-lineage/v1` manifest to make the production evidence package inspectable. The manifest separates file facts from historical claims. Passing validation means that the package is structurally and pixel-consistent; it does not prove how an image was created.

## Evidence levels

| Level | Meaning |
| --- | --- |
| `MACHINE-VERIFIED` | The validator directly checked JSON structure, references, local file bytes, decoded image properties, frame coverage, declarations, or sheet pixels. |
| `DECLARED` | The manifest records a creative-history claim. The validator can check that the declaration is present and internally consistent, but cannot observe the historical act. |
| `REVIEWED` | The manifest records human approval. The validator can check the review record and its subject reference, but a human must assess its authenticity and quality. |

Generation method, use of reference images, outline timing, use of adjacent keyframes, and the number or method of resize operations are historical facts. They remain `DECLARED` even when their records pass every structural check. Approval remains `REVIEWED`.

Unknown object fields are allowed so evidence collectors can add notes, timestamps, tool versions, and repository-specific data without changing the v1 contract. Required v1 fields retain their defined types and meanings. Artifact types, relation types, review stages, and transform types are closed vocabularies; an extension field cannot introduce another production branch. A future incompatible contract must use a new `schema_version`.

## Manifest shape

Paths are UTF-8 strings resolved relative to the manifest file. Frame indices are zero-based global positions in the final spritesheet, including when multiple clips share one sheet. Every artifact is an image and supplies `id`, `type`, `path`, lowercase `sha256`, `width`, `height`, and `mode`. The validator opens the file rather than trusting the declared image metadata.

The allowed artifact types are `high-resolution-pre-master`, `canonical-master`, `high-resolution-keyframe`, `high-resolution-in-between`, `target-frame`, and `spritesheet`. The allowed relation types are `canonical-lock`, `canonical-reference`, and `adjacent-keyframe-reference`.

```json
{
  "schema_version": "spritesheet-lineage/v1",
  "contract": {
    "frame_width": 96,
    "frame_height": 96,
    "frame_count": 4,
    "canonical_short_side": 512,
    "outline": {
      "enabled": true,
      "target_width": 2
    }
  },
  "artifacts": [
    {
      "id": "pre-master-east",
      "type": "high-resolution-pre-master",
      "path": "evidence/pre-master-east.png",
      "sha256": "<64 lowercase hexadecimal characters>",
      "width": 512,
      "height": 512,
      "mode": "RGBA"
    },
    {
      "id": "master-east",
      "type": "canonical-master",
      "path": "evidence/master-east.png",
      "sha256": "<sha256>",
      "width": 512,
      "height": 512,
      "mode": "RGBA"
    },
    {
      "id": "walk-east-k00",
      "type": "high-resolution-keyframe",
      "path": "evidence/walk-east-k00.png",
      "sha256": "<sha256>",
      "width": 512,
      "height": 512,
      "mode": "RGBA"
    },
    {
      "id": "walk-east-i01",
      "type": "high-resolution-in-between",
      "path": "evidence/walk-east-i01.png",
      "sha256": "<sha256>",
      "width": 512,
      "height": 512,
      "mode": "RGBA"
    },
    {
      "id": "walk-east-t00",
      "type": "target-frame",
      "path": "target/walk-east-00.png",
      "sha256": "<sha256>",
      "width": 96,
      "height": 96,
      "mode": "RGBA"
    },
    {
      "id": "walk-sheet",
      "type": "spritesheet",
      "path": "target/walk.png",
      "sha256": "<sha256>",
      "width": 192,
      "height": 192,
      "mode": "RGBA"
    }
  ],
  "relations": [
    {
      "id": "lock-master-east",
      "type": "canonical-lock",
      "sources": ["pre-master-east"],
      "target": "master-east",
      "outline_enabled": true,
      "outline_target_width": 2
    },
    {
      "id": "reference-walk-east-k00",
      "type": "canonical-reference",
      "sources": ["master-east"],
      "target": "walk-east-k00"
    },
    {
      "id": "bracket-walk-east-i01",
      "type": "adjacent-keyframe-reference",
      "sources": ["walk-east-k00", "walk-east-k03"],
      "target": "walk-east-i01"
    }
  ],
  "clips": [
    {
      "id": "walk-east",
      "loop": false,
      "repeated_closing_target": false,
      "frames": [
        {
          "index": 0,
          "role": "keyframe",
          "high_resolution": "walk-east-k00",
          "target": "walk-east-t00"
        },
        {
          "index": 1,
          "role": "in-between",
          "high_resolution": "walk-east-i01",
          "target": "walk-east-t01",
          "previous_keyframe": 0,
          "next_keyframe": 3
        },
        {
          "index": 2,
          "role": "in-between",
          "high_resolution": "walk-east-i02",
          "target": "walk-east-t02",
          "previous_keyframe": 0,
          "next_keyframe": 3
        },
        {
          "index": 3,
          "role": "keyframe",
          "high_resolution": "walk-east-k03",
          "target": "walk-east-t03"
        }
      ]
    }
  ],
  "reviews": [
    {
      "id": "review-master-east",
      "subject": "master-east",
      "stage": "canonical-lock",
      "status": "approved",
      "reviewer": "human-reviewer-id",
      "declared_order": 1
    }
  ],
  "transforms": [
    {
      "id": "downsample-walk-east-00",
      "type": "downsample",
      "source": "walk-east-k00",
      "target": "walk-east-t00",
      "declared_resize_count": 1,
      "declared_order": 6
    }
  ],
  "assembly": {
    "sheet": "walk-sheet",
    "columns": 2,
    "rows": 2,
    "order": "row-major",
    "targets": [
      "walk-east-t00",
      "walk-east-t01",
      "walk-east-t02",
      "walk-east-t03"
    ]
  }
}
```

The example abbreviates repeated artifacts, relations, reviews, and transforms. A valid package includes the referenced records for every frame.

When outline is disabled, use `"enabled": false` and `"target_width": "none"`. Every `canonical-master` requires exactly one `canonical-lock` relation from a `high-resolution-pre-master`; its outline fields must equal `contract.outline`. A disabled-outline canonical master must be pixel-identical to its pre-master. For an enabled outline, the actual application of the outline before canonical lock remains `DECLARED`.

Every high-resolution pre-master, canonical master, keyframe, and in-between must use the exact fixed high-resolution canvas derived from the target frame aspect ratio with a `512 px` short side. Every high-resolution keyframe requires exactly one `canonical-reference` relation, and every keyframe in one clip must reference the same directional canonical master. Each clip contains at least two keyframes and at least two in-betweens. Every high-resolution frame artifact is consumed by exactly one global frame, and every decoded high-resolution image is distinct from the other images with the same role in that clip.

Every clip declares `loop` and `repeated_closing_target` as booleans. An in-between names the indices of the immediately preceding and following keyframes; those declarations must match the adjacent keyframes in that clip. When `loop` is `true`, a tail or head interval may wrap from the final keyframe to the first keyframe. Each in-between also requires exactly one `adjacent-keyframe-reference` relation whose two distinct ordered sources are those keyframe artifacts and whose target is the in-between artifact.

The `loop` field records playback intent; it does not mechanically prove visual or velocity continuity across the seam. Set `repeated_closing_target` to `true` only for a loop whose contract requires it. In that case, the final target pixels must exactly equal the opening target pixels, no other target pair in the clip may be identical, and the closing frame must still have its own distinct, independently generated high-resolution source and its own single downsample declaration. When the field is `false`, every target frame in the clip must be pixel-distinct. Do not reuse a high-resolution artifact or copy a terminal target frame to create the closing cell.

The union of clip frame indices must equal the final sheet's global range `0..contract.frame_count - 1` exactly once and in order. Within each clip, every keyframe index names a distinct high-resolution keyframe artifact and every in-between index names a distinct high-resolution in-between artifact. Every frame names one unique target artifact. Every target has exactly one matching `downsample` declaration from that frame's high-resolution artifact, with `declared_resize_count` equal to `1`. This count is a declaration of the transform history, not a pixel-provable fact.

Every canonical master, high-resolution keyframe, and high-resolution in-between requires at least one `approved` review record. The only valid subject-specific stages are `canonical-lock`, `keyframe-approval`, and `in-between-approval`. Every review and downsample record has a unique positive `declared_order`. The declared order must place canonical lock before keyframe approval, all keyframe approvals for a clip before its in-between approvals, and the complete clip review before every downsample declaration. The validator checks this ordering structure, but reports the approval and historical-order claims as `REVIEWED` or `DECLARED` rather than authenticating them.

The production artifact graph is closed. Every recorded pre-master, canonical master, high-resolution frame, target frame, and spritesheet must be consumed by the required relation, clip frame, downsample declaration, or assembly record. Review controls, contact sheets, unused candidates, and alternate branches must not be entered as production artifacts.

Assembly is a fixed rectangular grid. `targets` must equal clip frame order. The sheet dimensions must equal `columns * frame_width` by `rows * frame_height`; every used cell must exactly match its target RGBA pixels, and unused cells must have zero Alpha. Both row-major and column-major order are supported.

## Validation

Run from any working directory:

```bash
PYTHONDONTWRITEBYTECODE=1 <python> <skill-dir>/scripts/validate_lineage.py \
  --lineage path/to/lineage.json
```

Exit code `0` means no `MACHINE-VERIFIED` check failed. `DECLARED` and `REVIEWED` lines are evidence classifications, not warnings and not mechanical proof of history. Exit code `1` means the evidence package has at least one structural, reference, file, hash, image, coverage, transform-declaration, or assembly inconsistency.
