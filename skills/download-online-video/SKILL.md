---
name: download-online-video
description: Download user-authorized videos from Bilibili, Douyin, TikTok, X, and YouTube at the best available native quality or a requested resolution, then verify the local media file. Use when the user supplies a supported video URL and asks to save the video locally; do not use for DRM bypass, paywall circumvention, or unauthorized access.
---

# Download Online Video

Download the requested media as a real local file and report an evidence-backed result. Prefer `yt-dlp` for extraction, `ffmpeg` for stream merging or remuxing, and `ffprobe` for verification.

## Preserve the request

- Treat "original", "source", or "native" quality as the highest-quality source stream the platform exposes. Never upscale and call it original.
- Honor an explicit resolution cap or codec/container requirement. If the exact request is unavailable, select the closest non-upscaled result and disclose the mismatch.
- Download only the referenced item by default. Use `--no-playlist` unless the user explicitly requests a playlist, channel, collection, series, or multi-item post.
- A URL playback-time parameter is not a trim request. Preserve the complete video unless the user supplies an explicit time range.
- Save in the user-specified directory, or the current task directory when none is specified. Avoid overwriting existing files.
- Do not download subtitles, thumbnails, comments, metadata sidecars, or alternate audio tracks unless requested.

## Access and privacy boundary

Proceed only with public media or content the user is authorized to access. Do not defeat DRM, a paywall, geographic access controls, account permissions, or other technical access restrictions.

Try public extraction without cookies first. When extraction requires a login and the user is already authorized in a local browser, `--cookies-from-browser <browser>` may be used without printing, exporting, or copying cookie contents. Never persist a cookie file unless the user explicitly requests it and understands the exposure risk.

## Workflow

1. Normalize the URL without removing selectors such as an X `/video/2` suffix or a Bilibili page index. Quote URLs in shell commands.
2. Inspect the local tools. Use an existing current `yt-dlp`; if absent, install `yt-dlp[default]` in a task-local virtual environment rather than modifying system Python. Locate `ffmpeg` and `ffprobe` before choosing separate video and audio streams.
3. Probe the source before downloading:

   ```bash
   yt-dlp --no-playlist --list-formats "URL"
   ```

   Add authorized browser cookies only if the public probe fails for an access reason. Read [references/platforms-and-recovery.md](references/platforms-and-recovery.md) when the site requires platform-specific handling or extraction fails.
4. Choose formats from the observed list:
   - For highest native quality, prefer the best source video plus the best compatible source audio. A same-quality progressive file is preferable when it avoids an unnecessary merge.
   - For a resolution cap, select the best video at or below the requested height plus compatible audio. Do not silently choose a higher resolution.
   - Preserve source codecs and remux when possible. Transcode only when the user requests compatibility or the target container cannot carry the selected streams.
   - Do not infer quality solely from file size or a format label; compare resolution, bitrate, frame rate, codec, dynamic range, and whether audio is present.
5. Download with an unambiguous output template and `--no-overwrites`. A typical adaptive-stream command is:

   ```bash
   yt-dlp --no-playlist --no-overwrites \
     -f "bestvideo*+bestaudio/best" \
     --merge-output-format mp4 \
     -o "%(extractor)s_%(id)s_%(title).80B.%(ext)s" \
     "URL"
   ```

   Treat this as a starting shape, not a substitute for the format inspection. Use explicit format IDs when they better preserve the requested native quality or codec.
6. Verify the final artifact with `ffprobe`. Confirm the file is non-empty and inspect at least container, duration, video codec, width, height, frame rate, audio codec, sample rate, channels, and file size. If the source has no audio, say so rather than treating it as a successful audio download.
7. Remove or move aside only temporary files created by this run. Do not remove pre-existing media or unrelated work.

## Result contract

Return a clickable absolute file path and report:

- actual resolution and frame rate;
- video and audio codecs;
- duration and file size;
- whether this is the highest native source tier or a user-requested cap;
- any material mismatch, missing stream, authentication dependency, or source limitation.

Do not claim success until the final file passes inspection. Distinguish platform-advertised estimates from properties verified on the downloaded file.
