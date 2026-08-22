#!/usr/bin/env python3
"""Build a standalone HTML diagnostic board for app-logo candidates.

The board is a first-pass visual proxy. It does not prove user recognition,
platform approval, store conversion, or legal distinctiveness.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
from pathlib import Path
import sys
from typing import Any, Dict, List
import xml.etree.ElementTree as ET


SUPPORTED_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
MAX_ASSET_BYTES = 12 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a standalone app-icon test board from SVG or raster candidates."
    )
    parser.add_argument("assets", nargs="+", help="Candidate SVG, PNG, JPEG, or WebP files")
    parser.add_argument("--output", "-o", required=True, help="Output HTML path")
    parser.add_argument("--title", default="App Logo Diagnostic Board", help="Board title")
    return parser.parse_args()


def validate_svg(data: bytes, path: Path) -> List[str]:
    try:
        root = ET.fromstring(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ValueError(f"{path}: invalid SVG: {exc}") from exc

    if root.tag.split("}")[-1] != "svg":
        raise ValueError(f"{path}: root element is not <svg>")

    warnings: List[str] = []
    if "viewBox" not in root.attrib:
        warnings.append("No viewBox; scaling may be unreliable.")

    for element in root.iter():
        local_tag = element.tag.split("}")[-1]
        if local_tag in {"script", "foreignObject"}:
            raise ValueError(f"{path}: unsupported active SVG element <{local_tag}>")
        for key, value in element.attrib.items():
            local_key = key.split("}")[-1].lower()
            if local_key.startswith("on"):
                raise ValueError(f"{path}: unsupported SVG event attribute {local_key}")
            if local_key in {"href", "src"} and value and not value.startswith(("#", "data:")):
                raise ValueError(f"{path}: external SVG reference is not self-contained: {value}")
    return warnings


def validate_raster(data: bytes, path: Path) -> None:
    suffix = path.suffix.lower()
    valid = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8"),
        ".jpeg": data.startswith(b"\xff\xd8"),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not valid.get(suffix, False):
        raise ValueError(f"{path}: file signature does not match {suffix}")


def load_asset(raw_path: str) -> Dict[str, Any]:
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{path}: file does not exist")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"{path}: unsupported file type {path.suffix or '(none)'}")

    data = path.read_bytes()
    if not data:
        raise ValueError(f"{path}: file is empty")
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError(f"{path}: asset exceeds {MAX_ASSET_BYTES // (1024 * 1024)} MiB")

    warnings: List[str] = []
    if path.suffix.lower() == ".svg":
        warnings.extend(validate_svg(data, path))
        mime = "image/svg+xml"
    else:
        validate_raster(data, path)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    encoded = base64.b64encode(data).decode("ascii")
    return {
        "name": path.stem,
        "filename": path.name,
        "uri": f"data:{mime};base64,{encoded}",
        "warnings": warnings,
    }


def icon_img(asset: Dict[str, Any]) -> str:
    name = html.escape(str(asset["name"]))
    uri = html.escape(str(asset["uri"]), quote=True)
    return f'<img class="candidate" src="{uri}" alt="{name}">'


def size_row(asset: Dict[str, Any]) -> str:
    cells = []
    for size in (16, 24, 32, 48, 64, 96, 128):
        cells.append(
            '<div class="size-cell">'
            f'<div class="pixel-box" style="width:{size}px;height:{size}px">{icon_img(asset)}</div>'
            f'<span>{size}px</span></div>'
        )
    return "".join(cells)


def mask_row(asset: Dict[str, Any]) -> str:
    masks = (
        ("square", "0"),
        ("rounded", "22%"),
        ("squircle proxy", "32%"),
        ("circle", "50%"),
    )
    return "".join(
        '<div class="mask-cell">'
        f'<div class="mask-frame" style="border-radius:{radius}">{icon_img(asset)}</div>'
        f'<span>{html.escape(label)}</span></div>'
        for label, radius in masks
    )


def background_row(asset: Dict[str, Any]) -> str:
    backgrounds = (
        ("light", "#ffffff"),
        ("dark", "#111318"),
        ("saturated", "#5b34f2"),
        ("warm", "#f5a623"),
        ("checker", "checker"),
    )
    cells = []
    for label, value in backgrounds:
        extra = " checker" if value == "checker" else ""
        style = "" if value == "checker" else f' style="background:{value}"'
        cells.append(
            f'<div class="context-cell{extra}"{style}>{icon_img(asset)}<span>{label}</span></div>'
        )
    return "".join(cells)


def crowded_field(asset: Dict[str, Any]) -> str:
    colors = (
        "#2684ff", "#ff5630", "#36b37e", "#6554c0", "#ffab00", "#00b8d9",
        "#172b4d", "#e91e63", "#7cb342", "#8d6e63", "#546e7a", "#f4511e",
    )
    tiles = []
    for index, color in enumerate(colors):
        if index == 7:
            tiles.append(f'<div class="home-icon target">{icon_img(asset)}<i class="badge">3</i></div>')
        else:
            shape = (index % 4) + 1
            tiles.append(
                f'<div class="home-icon synthetic" style="--tile:{color}"><i class="shape s{shape}"></i></div>'
            )
    return "".join(tiles)


def candidate_section(asset: Dict[str, Any], index: int) -> str:
    warning_items = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in asset["warnings"]
    )
    warnings = f'<ul class="warnings">{warning_items}</ul>' if warning_items else ""
    return f"""
    <section class="candidate-section" id="candidate-{index}">
      <header class="candidate-header">
        <div><span class="eyebrow">Candidate {index}</span><h2>{html.escape(str(asset['name']))}</h2></div>
        <code>{html.escape(str(asset['filename']))}</code>
      </header>
      {warnings}
      <div class="overview-grid">
        <article class="panel master-panel"><h3>Master and safe-area proxy</h3><div class="master-stage">{icon_img(asset)}<div class="safe-area"></div></div><p>The dashed circle is a visual proxy, not a platform specification.</p></article>
        <article class="panel"><h3>Synthetic crowded field</h3><div class="home-screen">{crowded_field(asset)}</div><p>Use real category icons and representative users for findability claims.</p></article>
      </div>
      <article class="panel"><h3>Small-size ladder</h3><div class="size-row">{size_row(asset)}</div></article>
      <article class="panel"><h3>Mask proxies</h3><div class="mask-row">{mask_row(asset)}</div></article>
      <article class="panel"><h3>Background stress</h3><div class="background-row">{background_row(asset)}</div></article>
    </section>
    """


def build_html(title: str, assets: List[Dict[str, Any]]) -> str:
    escaped_title = html.escape(title)
    nav = "".join(
        f'<a href="#candidate-{index}">{index}. {html.escape(str(asset["name"]))}</a>'
        for index, asset in enumerate(assets, start=1)
    )
    sections = "".join(
        candidate_section(asset, index) for index, asset in enumerate(assets, start=1)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>{escaped_title}</title>
<style>
:root{{--ink:#17181c;--muted:#666b76;--line:#dfe2e8;--paper:#f5f6f8;--panel:#fff;--accent:#3d5afe}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.topbar{{position:sticky;top:0;z-index:10;display:flex;gap:20px;align-items:center;justify-content:space-between;padding:18px 28px;background:rgba(245,246,248,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
.topbar h1{{margin:0;font-size:20px}}nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a{{padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);text-decoration:none}}
main{{width:min(1180px,calc(100% - 32px));margin:0 auto 80px}}.intro{{padding:42px 0 20px;color:var(--muted);max-width:820px}}
.candidate-section{{scroll-margin-top:90px;margin:22px 0 54px}}.candidate-header{{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}}.candidate-header h2{{margin:3px 0 0;font-size:32px}}.eyebrow{{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}}code{{color:var(--muted)}}
.overview-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.panel{{margin:14px 0;padding:18px;background:var(--panel);border:1px solid var(--line);border-radius:18px;box-shadow:0 10px 30px rgba(22,26,35,.04)}}.panel h3{{margin:0 0 16px;font-size:15px}}.panel p{{margin:12px 0 0;color:var(--muted);font-size:12px}}
.candidate{{display:block;width:100%;height:100%;object-fit:contain}}.master-stage{{position:relative;width:min(360px,100%);aspect-ratio:1;margin:auto;background:linear-gradient(135deg,#fff,#edf0f5);border:1px solid var(--line)}}.safe-area{{position:absolute;inset:17%;border:1px dashed rgba(61,90,254,.75);border-radius:50%;pointer-events:none}}
.size-row,.mask-row,.background-row{{display:flex;gap:18px;align-items:end;flex-wrap:wrap;min-height:150px}}.size-cell,.mask-cell{{display:flex;min-width:72px;flex-direction:column;gap:8px;align-items:center;color:var(--muted);font-size:11px}}.pixel-box{{background:#f1f3f7;box-shadow:0 0 0 1px var(--line)}}.mask-frame{{width:112px;height:112px;background:#f1f3f7;overflow:hidden;box-shadow:0 0 0 1px var(--line)}}
.context-cell{{position:relative;width:152px;height:152px;padding:16px;border:1px solid var(--line);overflow:hidden}}.context-cell span{{position:absolute;left:8px;bottom:6px;padding:2px 5px;background:rgba(255,255,255,.78);color:#252830;font-size:10px;border-radius:4px}}.checker{{background-color:#fff;background-image:linear-gradient(45deg,#d7d9df 25%,transparent 25%),linear-gradient(-45deg,#d7d9df 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#d7d9df 75%),linear-gradient(-45deg,transparent 75%,#d7d9df 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}}
.home-screen{{display:grid;grid-template-columns:repeat(4,64px);gap:18px;padding:24px;width:max-content;max-width:100%;background:linear-gradient(145deg,#dadff1,#aab6d7);border-radius:22px}}.home-icon{{position:relative;width:64px;height:64px;border-radius:16px;overflow:hidden;box-shadow:0 5px 12px rgba(20,25,40,.16)}}.synthetic{{display:grid;place-items:center;background:var(--tile)}}.shape{{display:block;width:31px;height:31px;background:rgba(255,255,255,.92)}}.s1{{border-radius:50%}}.s2{{transform:rotate(45deg);border-radius:5px}}.s3{{width:36px;height:12px;border-radius:8px;box-shadow:0 18px 0 rgba(255,255,255,.92)}}.s4{{clip-path:polygon(50% 0,100% 100%,0 100%)}}.badge{{position:absolute;right:-1px;top:-1px;display:grid;place-items:center;min-width:20px;height:20px;padding:0 5px;background:#f02638;color:#fff;border:2px solid #fff;border-radius:999px;font:700 10px/1 sans-serif}}
.warnings{{padding:12px 12px 12px 32px;background:#fff5d9;border:1px solid #f0cf71;border-radius:12px;color:#6b5000}}
@media(max-width:760px){{.topbar{{position:static;align-items:flex-start;flex-direction:column}}.overview-grid{{grid-template-columns:1fr}}.candidate-header{{align-items:flex-start;flex-direction:column}}.home-screen{{grid-template-columns:repeat(4,52px);gap:12px}}.home-icon{{width:52px;height:52px;border-radius:13px}}}}
@media print{{.topbar{{position:static}}.candidate-section{{break-before:page}}}}
</style>
</head>
<body>
<header class="topbar"><h1>{escaped_title}</h1><nav>{nav}</nav></header>
<main>
  <div class="intro"><p>This board exposes visual failure modes across sizes, masks, backgrounds, badges, and a synthetic crowded field. It is diagnostic evidence only; it does not prove recognition, platform approval, conversion, cultural safety, or legal clearance.</p></div>
  {sections}
</main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    try:
        assets = [load_asset(item) for item in args.assets]
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_html(args.title, assets), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    warning_count = sum(len(asset["warnings"]) for asset in assets)
    print(f"Wrote {output} with {len(assets)} candidate(s) and {warning_count} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
