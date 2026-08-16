---
name: download-video-transcripts
description: Download captions or transcribe a single video from Bilibili, Douyin, YouTube, or X/Twitter, then deliver verified Chinese and English corrected transcripts and chaptered transcripts. Use for network-video subtitle download, caption extraction, bilingual transcript production, or local Whisper fallback when downloadable captions are unavailable.
---

# Download Video Transcripts

Produce a traceable bilingual transcript package from one explicitly supplied video URL. Default to unattended decisions. Enter interactive mode only when the user explicitly requests human confirmation.

## Load the contract

Read [references/workflow.md](references/workflow.md) before probing the URL. Read [references/delivery-contract.md](references/delivery-contract.md) before creating transcript files or the manifest.

## Guardrails

- Process one video or one explicitly addressed part. Never expand a playlist, anthology, or thread unless the user explicitly requests batch processing.
- Never bypass a paywall, entitlement, geographic restriction, age restriction, private-access boundary, signature control, or DRM. A logged-in account may supply a resource it is legitimately entitled to access only when the resource is non-DRM.
- Probe anonymously first. Escalate only after anonymous extraction fails or explicitly reports that authentication is required: Chrome `Default`, then Chrome `Profile 1`.
- Never print, copy, persist, summarize, or expose cookies, account names, authorization headers, or browser storage. Record only the browser profile label and a coarse success or failure category.
- Treat the selected source caption or source-language Whisper transcript as the sole textual authority. Never merge competing caption tracks.
- Preserve speaker claims. Correct recognition, segmentation, punctuation, and proper-name errors; never silently fact-check or rewrite what the speaker asserted.
- Publish `complete` only when all four bilingual deliverables and their provenance validate together.

## Execute the state machine

### 1. Establish the run

Create `outputs/<safe-title> [<platform-video-id>]/` for delivery and a task-local `work/` directory for downloads and intermediate files. Do not place source media inside the Skill directory.

Run the bootstrap script for the downloader. Install Whisper only if the workflow reaches the transcription branch.

```bash
python3 scripts/bootstrap_tools.py --component downloader
```

Use the returned absolute executable paths. Set `HF_HOME` to the returned shared Hugging Face cache when invoking Whisper.

Initialize `processing-manifest.json` as specified by the delivery contract. Record the decision mode as `unattended` unless the user explicitly requested `interactive`.

### 2. Probe without downloading media

Use `yt-dlp --dump-single-json --skip-download` and capture stdout and stderr into separate task-local files. Reject playlist or multi-entry expansion. Preserve the successful metadata JSON as run evidence.

If anonymous extraction fails or reports that authentication is required, retry with Chrome `Default`, then Chrome `Profile 1`. Stop after the first successful extraction. Follow the exact escalation and paywall rules in the workflow reference.

### 3. Inventory and select captions

Pass the successful metadata JSON to:

```bash
python3 scripts/subtitle_inventory.py --info <info.json> --output <inventory.json>
```

In interactive mode, show every normalized track with language, manual or automatic origin, available formats, and ranking tier; wait for the user to choose exactly one source track.

In unattended mode, use the inventory order:

1. original-language manual captions;
2. original-language automatic captions;
3. manual captions with the greatest measured coverage;
4. automatic captions with the greatest measured coverage;
5. platform default, then stable lexical order as the last tie-break.

When multiple tracks tie in tier 3 or 4, download those candidate captions, preserve each native file, convert a copy to SRT, and rerun `subtitle_inventory.py` with one `--candidate-file KIND:LANGUAGE=PATH` argument per candidate. Select the reported `chosen` track. Record the inventory and reason in the manifest.

If a source track exists, download that track without downloading media. Preserve its native file and create `source/source-timeline.srt`. Continue at step 5.

### 4. Transcribe only when captions cannot supply the source

Enter this branch when no downloadable captions exist, or when caption retrieval still fails after bounded retries. A public or legitimately entitled non-DRM media stream must be available. Stop with `blocked` when the only source crosses a paywall or access boundary.

Download the complete selected video as a task-local intermediate file. Prefer a broadly compatible H.264/AAC MP4 when available, but never request an inaccessible premium format. Verify duration, codecs, and stream presence with `ffprobe`.

Install the local transcriber:

```bash
python3 scripts/bootstrap_tools.py --component whisper
```

Run `mlx_whisper` with `mlx-community/whisper-large-v3-turbo`, automatic source-language detection, transcription mode, word timestamps, and JSON plus SRT and TXT output. Store the raw JSON as `source/whisper.json` and the normalized timeline as `source/source-timeline.srt`. Mark uncertain audio with timestamps rather than guessing.

### 5. Correct the source before translating

Create a source-language corrected transcript from the selected caption or Whisper timeline. Preserve meaningful speech repetitions, self-corrections, fillers, and comprehension-relevant sound cues. Remove only demonstrable recognition hallucinations and decorative repeated cues. Retain reliable source-provided speaker labels; never infer speakers.

If the source language is neither Chinese nor English, also deliver `source/source-corrected.txt`. If it is Chinese or English, the matching bilingual corrected transcript is the source-corrected transcript.

Generate Chinese and English independently from the corrected source. Never create one translation by back-translating the other. Keep proper names, numbers, qualifiers, uncertainty, and claim strength aligned. Use `[inaudible HH:MM:SS]` or its faithful localized equivalent for unresolved audio.

### 6. Create chaptered transcripts

Create the Chinese and English chaptered transcripts with matching structure. Add only titles, sections, subsections, paragraphs, lists, and clearly delimited prompt or quotation blocks. Preserve the source order and all substantive content. Do not summarize, expand, fact-correct, or reorganize the argument.

### 7. Finalize atomically

Run the delivery validator with every required artifact:

```bash
python3 scripts/finalize_delivery.py \
  --root <delivery-root> \
  --manifest <delivery-root>/processing-manifest.json \
  --require source/metadata.json \
  --require source/subtitle-inventory.json \
  --require source/source-timeline.srt \
  --require zh/corrected-transcript.txt \
  --require zh/chaptered-transcript.md \
  --require en/corrected-transcript.txt \
  --require en/chaptered-transcript.md
```

For the caption branch, also require the selected `source/raw-subtitle.<native-extension>`. For the Whisper branch, also require `source/whisper.json`. For a non-Chinese, non-English source, also require `source/source-corrected.txt`.

If validation reports `complete`, delete task-local downloaded media unless the user explicitly requested the video as a deliverable. If it reports `incomplete`, retain raw evidence and diagnostics, report the incomplete state, and do not present partial bilingual files as a completed package.

## Completion criteria

Complete only when:

- the exact single-video identity and selected source track or Whisper fallback are recorded;
- every access escalation and paywall decision is auditable without secret material;
- the raw source, source timeline, four bilingual deliverables, and conditional source artifacts exist;
- Chinese and English chapter structures match and remain faithful to the corrected source;
- `finalize_delivery.py` returns success and records SHA-256 for every artifact;
- temporary media is removed after success unless retention was explicitly requested.
