# Platform Handling and Recovery

Read only the section relevant to the current source or failure. Platform extractors change frequently, so verify behavior with the installed `yt-dlp` instead of assuming every listed site currently works.

## Bilibili

- Accept canonical `bilibili.com` URLs and resolved `b23.tv` share links.
- Preserve a requested page or episode selector. Default to one video, not an entire collection, favorites list, season, or uploader feed.
- Higher tiers may require an authorized logged-in browser account, and some tiers may depend on the account's subscription. Use browser cookies only for access the user already has.
- Bilibili commonly exposes separate DASH video and audio streams; require `ffmpeg` for merging and verify the merged audio stream.

## Douyin

- Resolve short share URLs through `yt-dlp`; do not replace them with third-party downloader sites.
- Strip prose copied around a share URL, but preserve URL query data until extraction succeeds.
- Public extraction can change rapidly. If the extractor fails, update the task-local `yt-dlp`, retry once, and then report the current platform limitation rather than looping or invoking an untrusted service.

## TikTok

- Use the exact post URL and default to a single post.
- Try without cookies first. If TikTok returns a login or verification barrier, authorized browser cookies may help; they are not permission to bypass a CAPTCHA or account restriction.
- Prefer a source format without a watermark when the platform directly exposes one through the authorized session. Do not use third-party watermark-removal or reconstruction services.

## X

- Preserve `/video/N` when a post contains multiple videos. `--no-playlist` should select only the URL-addressed media item when supported by the extractor.
- Compare progressive HTTP and HLS variants. A high-bitrate progressive MP4 can be the best complete source even when an HLS video-only rendition is also listed.
- Verify the actual dimensions; X may expose nonstandard widths such as `1882x1080` rather than a nominal `1920x1080`.

## YouTube

- YouTube often exposes the highest-quality video and audio separately. Inspect formats and merge explicit IDs when generic selection would choose an unwanted codec or container.
- If the user requests broad playback compatibility, prefer H.264 video plus AAC audio in MP4 when available at the requested resolution. Quality-first requests may appropriately retain VP9, AV1, Opus, HDR, or higher frame rate source streams.
- For bot or login challenges, use an authorized local browser session without exporting cookies.
- For JavaScript challenge failures, prefer a current official executable or install `yt-dlp[default]`, which includes the matching EJS component. If needed, enable an installed supported runtime with `--js-runtimes`; use `--remote-components ejs:github` only as a targeted recovery because it permits fetching executable components from the official yt-dlp EJS repository.

## Failure recovery

Use a bounded progression and stop once the cause is established:

1. Re-run the probe with verbose diagnostics, taking care not to expose cookies, tokens, signed URLs, or personal browser data in the user response.
2. Confirm the URL points to a video and that the item is still available.
3. Update only a task-local `yt-dlp` installation and retry once.
4. Add authorized browser cookies only for a demonstrated access or bot-check failure.
5. Confirm `ffmpeg` is available when adaptive streams require merging.
6. Re-probe expired manifests or signed URLs instead of retrying stale media URLs.
7. If extraction is still blocked, report the exact class of limitation and leave no misleading partial file.

Never fall back to unknown downloader websites, browser extensions, or credential-export tools merely to force a result.
