# Workflow reference

## State model

Use these states in `processing-manifest.json`:

`initialized -> probed -> source-selected -> source-acquired -> corrected -> translated -> chaptered -> complete`

Terminal non-success states are `blocked` and `incomplete`. Record every transition with an ISO 8601 timestamp and a short reason.

## Tool cache

Use `~/.codex/cache/download-video-transcripts/` as the persistent cache. `bootstrap_tools.py` creates:

- `venv/` for `yt-dlp` and `mlx-whisper`;
- `huggingface/` for `mlx-community/whisper-large-v3-turbo`.

Never store media, captions, browser data, or transcripts in this cache.

## Probe sequence

Run each probe with stdout and stderr separated. Never place secrets in command output included in the final response.

1. Anonymous.
2. `--cookies-from-browser chrome:Default` after anonymous failure or an explicit authentication requirement.
3. `--cookies-from-browser 'chrome:Profile 1'` if Default fails.

Stop after the first successful metadata extraction. A successful anonymous probe with no captions does not by itself authorize cookie escalation.

Treat login challenges, bot challenges, and extractor authentication errors as authentication requirements. Treat premium-only, purchase-only, private, geographic, age, and DRM errors as access-boundary signals, not authentication retry hints, unless the current logged-in account is explicitly shown to possess the entitlement.

Using a legitimate logged-in entitlement is allowed only for a non-DRM resource exposed normally to that account. Never alter entitlement parameters, forge signatures, reuse another account's tokens, or infer hidden media URLs.

## Caption acquisition

Treat both `subtitles` and `automatic_captions` in the extractor metadata as downloadable captions. Keep their origin distinct.

Download only the selected language after selection. When coverage must break a ranking tie, download only the tied candidates. Preserve native caption files before conversion. Create SRT copies for coverage measurement and the source timeline.

Coverage is the union of timed cue intervals divided by video duration. Cue count breaks equal coverage; platform default breaks the next tie; a stable language key breaks the last tie.

Bound caption download retries to three attempts with increasing short delays. After the third failure:

- in interactive mode, ask before entering the media branch;
- in unattended mode, enter the media branch automatically if a permitted media stream exists;
- otherwise record `blocked` with the extractor error category.

## Media and Whisper branch

Download the complete addressed video, not a clip implied only by a playback-start query parameter. Never expand a playlist.

Prefer native H.264 video plus AAC audio when available. Otherwise accept a freely accessible format that `ffmpeg` can decode. Verify the final intermediate with `ffprobe`:

- one video stream;
- one audio stream;
- positive duration;
- a non-empty container.

Invoke Whisper with:

- model `mlx-community/whisper-large-v3-turbo`;
- task `transcribe`;
- language auto-detection;
- word timestamps enabled;
- raw JSON, SRT, and TXT outputs;
- `HF_HOME=~/.codex/cache/download-video-transcripts/huggingface`.

Do not translate with Whisper. Correct the source-language transcript first, then translate the corrected source separately into Chinese and English.

## Text integrity

The corrected transcript may repair:

- homophone and recognition errors supported by context;
- punctuation and sentence boundaries;
- capitalization and established proper-name spelling;
- duplicated decoder hallucinations that cannot fit their timestamp duration.

The corrected transcript must retain:

- claims, numbers, hedges, and contradictions;
- meaningful repetitions and self-corrections;
- uncertainty with timestamps;
- reliable source-provided speaker and sound labels.

The chaptered transcript may add structure only. Keep the complete corrected content in source order. Chinese and English chapter headings must map one-to-one.

## Multi-media pages

Honor an explicit part or media index in the URL. Otherwise process the first platform-ordered video and record its index. Do not expand playlists, Bilibili anthologies, X threads, or other collections without an explicit batch request.

## Cleanup

After atomic validation succeeds, remove task-local video, audio, candidate captions used only for comparison, and transient extraction files. Retain the selected raw caption, source timeline, raw Whisper JSON when applicable, final transcripts, manifest, and requested video deliverable.
