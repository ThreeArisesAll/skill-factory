#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
entries = []
for path in ROOT.rglob('*'):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    if rel == 'SHA256SUMS' or '__pycache__' in path.parts or path.suffix == '.pyc' or path.name == '.DS_Store':
        continue
    entries.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
entries.sort()
(ROOT / 'SHA256SUMS').write_text(''.join(f'{digest}  {rel}\n' for rel, digest in entries), encoding='utf-8')
print(f'WROTE: {len(entries)} checksums')
