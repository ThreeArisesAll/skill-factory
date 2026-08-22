# Delivery contract

## Directory layout

```text
<safe-title> [<platform-video-id>]/
├── processing-manifest.json
├── source/
│   ├── metadata.json
│   ├── subtitle-inventory.json
│   ├── raw-subtitle.<native-extension>      # Caption branch
│   ├── source-timeline.srt
│   ├── whisper.json                         # Whisper branch
│   └── source-corrected.txt                 # Source is neither zh nor en
├── zh/
│   ├── corrected-transcript.txt
│   └── chaptered-transcript.md
└── en/
    ├── corrected-transcript.txt
    └── chaptered-transcript.md
```

Keep `raw-subtitle.<native-extension>` byte-for-byte as downloaded. Extra diagnostic files may live under `source/diagnostics/` while status is `blocked` or `incomplete`.

## Manifest shape

Start with this shape and extend it without removing required fields:

```json
{
  "schema_version": "video-transcript-package/v1",
  "status": "initialized",
  "source": {
    "url": "https://example.invalid/video",
    "platform": "youtube",
    "video_id": "id",
    "title": "title",
    "duration_seconds": 0,
    "media_index": 1
  },
  "decision_mode": "unattended",
  "access": {
    "probe_attempts": [],
    "selected_browser_profile": null,
    "used_authenticated_entitlement": false,
    "paywall_outcome": "not_detected",
    "drm_outcome": "not_detected"
  },
  "captions": {
    "tracks": [],
    "selected": null,
    "selection_reason": null
  },
  "transcription": {
    "used": false,
    "model": null,
    "detected_language": null
  },
  "lineage": {
    "source_authority": null,
    "source_corrected": null,
    "chinese_from": null,
    "english_from": null
  },
  "warnings": [],
  "uncertain_segments": [],
  "transitions": [],
  "artifacts": [],
  "validation": {
    "required": [],
    "missing": []
  }
}
```

Never include cookies, account identifiers, authorization headers, signed media URLs, or browser-storage values.

## Artifact records

`finalize_delivery.py` replaces `artifacts` with every regular delivery file except the manifest itself. Each record contains:

- `path`: POSIX path relative to the delivery root;
- `bytes`: exact byte length;
- `sha256`: lowercase hexadecimal SHA-256.

The validator sets `status` to `complete` only when every required path exists, is a regular file, is non-empty, stays inside the delivery root, and hashes successfully. It also requires the Chinese and English chapter files to have the same non-empty Markdown heading-level sequence. The validator appends the resulting terminal transition. Otherwise it sets `status` to `incomplete` and exits non-zero.

Mechanical validation does not prove semantic completeness, translation fidelity, or heading equivalence. Review those three properties against the corrected source before running the validator; record the review outcome in the manifest.

## Language requirements

`zh/corrected-transcript.txt` and `en/corrected-transcript.txt` contain the complete corrected transcript, not a summary. `zh/chaptered-transcript.md` and `en/chaptered-transcript.md` contain the same complete content with matching hierarchy.

When the source is Chinese, `zh/corrected-transcript.txt` is the corrected source. When the source is English, `en/corrected-transcript.txt` is the corrected source. For every other source language, retain `source/source-corrected.txt` and translate it independently into both target languages.
