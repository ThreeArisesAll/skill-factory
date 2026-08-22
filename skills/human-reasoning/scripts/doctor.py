#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COUNT = 100
NEW_COUNT = 1024
TOTAL_COUNT = 1124
TRACK_COUNT = 32
PASS_COUNT = 32
BASE_FINAL_HASH = '324aec2e67886ba25b8f36b51b8df53009531ea9f1cef9aa6a9f06389704c493'


def fail(message: str) -> None:
    print(f'FAIL: {message}')
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f'PASS: {message}')


def load_json(rel: str):
    path = ROOT / rel
    if not path.exists():
        fail(f'missing {rel}')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        fail(f'invalid JSON in {rel}: {exc}')


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not match:
        fail('SKILL.md has no valid YAML-style front matter')
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def canonical_hash(record: dict) -> str:
    payload = {k: v for k, v in record.items() if k != 'chain_hash'}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def verify_skill() -> None:
    path = ROOT / 'SKILL.md'
    if not path.exists():
        fail('SKILL.md is missing')
    text = path.read_text(encoding='utf-8')
    fm = parse_frontmatter(text)
    if fm.get('name') != 'human-reasoning':
        fail('front matter name must be human-reasoning')
    if not fm.get('description') or len(fm['description']) < 120:
        fail('front matter description is missing or too vague')
    required = [
        'B — Bind to human reality',
        'R — Recognize relevant asymmetries',
        'I — Import missing contact with reality',
        'D — Deliberate beyond language',
        'G — Give judgment and preserve ownership',
        'E — Execute a learning move',
        'Behavioral competence', 'Mechanism', 'Functional state',
        'Experience', 'Normative status',
        'Fast:', 'Deliberate:', 'Critical:',
        'facts, inferences, assumptions, values, and unknowns',
        'raw private chain-of-thought',
        'Human in the loop',
        'Stop when',
    ]
    low = text.lower()
    for token in required:
        if token.lower() not in low:
            fail(f'required concept missing from SKILL.md: {token}')
    words = re.findall(r"\b[\w–—'-]+\b", text)
    if len(words) > 3800:
        fail(f'SKILL.md exceeds 3800-word budget: {len(words)}')
    ok(f'front matter, BRIDGE protocol, claim levels, safeguards, and stop rule ({len(words)} words)')


def verify_matrix() -> tuple[list[dict], list[dict]]:
    tracks_doc = load_json('references/asymmetry-matrix.json')
    tracks = tracks_doc.get('tracks', [])
    if tracks_doc.get('count') != TRACK_COUNT or len(tracks) != TRACK_COUNT:
        fail(f'expected {TRACK_COUNT} asymmetry tracks')
    ids = [t.get('id') for t in tracks]
    slugs = [t.get('slug') for t in tracks]
    if ids != list(range(1, TRACK_COUNT + 1)):
        fail('track IDs are not ordered 1..32')
    if len(slugs) != len(set(slugs)):
        fail('track slugs are not unique')
    required_track = {
        'id','slug','name_en','name_zh','human_feature','ai_condition','risk','control',
        'runtime_check','ai_strength','trigger','human_input','evidence','owner','observable',
        'eval_prompt','must','must_not','sources'
    }
    for t in tracks:
        missing = required_track - set(t)
        if missing:
            fail(f"track {t.get('id')} missing fields: {sorted(missing)}")
        if not t['must'] or not t['must_not']:
            fail(f"track {t['id']} has empty test constraints")

    passes_doc = load_json('iterations/refinement-passes.json')
    passes = passes_doc.get('passes', [])
    if passes_doc.get('count') != PASS_COUNT or len(passes) != PASS_COUNT:
        fail(f'expected {PASS_COUNT} refinement passes')
    if [p.get('id') for p in passes] != list(range(1, PASS_COUNT + 1)):
        fail('pass IDs are not ordered 1..32')
    if len({p.get('slug') for p in passes}) != PASS_COUNT:
        fail('pass slugs are not unique')
    ok('32 asymmetry tracks and 32 refinement passes')
    return tracks, passes


def verify_iterations(tracks: list[dict], passes: list[dict]) -> str:
    ledger = load_json('iterations/iteration-log.json')
    base = load_json('iterations/base-v1.100.json')
    records = ledger.get('iterations', [])
    if ledger.get('base_count') != BASE_COUNT or ledger.get('new_count') != NEW_COUNT or ledger.get('count') != TOTAL_COUNT:
        fail('iteration count metadata is incorrect')
    if len(records) != TOTAL_COUNT:
        fail(f'expected {TOTAL_COUNT} records, found {len(records)}')
    if base.get('count') != BASE_COUNT or base.get('final_chain_hash') != BASE_FINAL_HASH:
        fail('base-v1.100 metadata mismatch')
    if records[:BASE_COUNT] != base.get('iterations'):
        fail('the preserved first 100 records differ from v1.100 base')
    if ledger.get('base_final_chain_hash') != BASE_FINAL_HASH:
        fail('base anchor hash mismatch')

    previous = '0' * 64
    pairs: set[tuple[int,int]] = set()
    track_slugs = {t['id']: t['slug'] for t in tracks}
    pass_slugs = {p['id']: p['slug'] for p in passes}
    for expected, record in enumerate(records, 1):
        if record.get('iteration') != expected:
            fail(f'iteration order mismatch at {expected}')
        if record.get('previous_hash') != previous:
            fail(f'previous hash mismatch at iteration {expected}')
        calculated = canonical_hash(record)
        if record.get('chain_hash') != calculated:
            fail(f'chain hash mismatch at iteration {expected}')
        previous = calculated
        round_file = ROOT / 'iterations' / 'rounds' / f'{expected:04d}.md'
        if not round_file.exists():
            fail(f'missing round file {round_file.name}')
        if expected > BASE_COUNT:
            new_i = expected - BASE_COUNT
            track_id = (new_i - 1) // PASS_COUNT + 1
            pass_id = (new_i - 1) % PASS_COUNT + 1
            if record.get('new_iteration') != new_i:
                fail(f'new_iteration mismatch at {expected}')
            if record.get('track_id') != track_id or record.get('pass_id') != pass_id:
                fail(f'matrix coordinate mismatch at {expected}')
            if record.get('track_slug') != track_slugs[track_id]:
                fail(f'track slug mismatch at {expected}')
            if record.get('pass_slug') != pass_slugs[pass_id]:
                fail(f'pass slug mismatch at {expected}')
            pairs.add((track_id, pass_id))
    if previous != ledger.get('final_chain_hash'):
        fail('final chain hash mismatch')
    if records[BASE_COUNT]['previous_hash'] != BASE_FINAL_HASH:
        fail('iteration 101 does not continue from v1.100 final hash')
    expected_pairs = {(t, p) for t in range(1, TRACK_COUNT + 1) for p in range(1, PASS_COUNT + 1)}
    if pairs != expected_pairs:
        fail('32×32 matrix does not cover every unique cell')
    round_names = {p.name for p in (ROOT / 'iterations' / 'rounds').glob('*.md')}
    expected_names = {f'{i:04d}.md' for i in range(1, TOTAL_COUNT + 1)}
    if round_names != expected_names:
        fail('round file set has missing or extra Markdown files')

    coverage = load_json('iterations/coverage-matrix.json')
    cells = coverage.get('cells', [])
    if coverage.get('count') != NEW_COUNT or len(cells) != NEW_COUNT:
        fail('coverage-matrix.json count mismatch')
    cov_pairs = {(c.get('track_id'), c.get('pass_id')) for c in cells}
    if cov_pairs != expected_pairs:
        fail('coverage-matrix.json does not contain every cell')
    ok('exact v1.100 base + 1024-cell matrix + 1124 ordered hash-chained records')
    return previous


def verify_tests(tracks: list[dict]) -> None:
    trigger = load_json('tests/trigger-cases.json')
    pos = trigger.get('positive', [])
    neg = trigger.get('negative', [])
    if len(pos) < 40 or len(neg) < 16:
        fail('trigger suite is too small')
    if len({c.get('id') for c in pos + neg}) != len(pos) + len(neg):
        fail('trigger IDs are not unique')

    behavior = load_json('tests/behavior-cases.json')
    if len(behavior) != TRACK_COUNT:
        fail('behavior suite must contain one case per track')
    if {c.get('track_id') for c in behavior} != set(range(1, TRACK_COUNT + 1)):
        fail('behavior suite does not cover all track IDs')
    if len({c.get('id') for c in behavior}) != TRACK_COUNT:
        fail('behavior IDs are not unique')
    for c in behavior:
        if len(c.get('must', [])) < 5 or len(c.get('must_not', [])) < 3:
            fail(f"behavior case {c.get('id')} has a weak rubric")

    anti = load_json('tests/anti-anthropomorphism-cases.json')
    if len(anti) < 16 or len({c.get('id') for c in anti}) != len(anti):
        fail('anti-anthropomorphism suite is too small or has duplicate IDs')
    if not (ROOT / 'evals' / 'trigger-prompts.csv').exists() or not (ROOT / 'evals' / 'behavior-prompts.jsonl').exists():
        fail('live eval fixtures are missing')
    ok(f'tests: {len(pos)} positive / {len(neg)} negative triggers; {len(behavior)} behavior; {len(anti)} anti-anthropomorphism')


def eligible_files() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel == 'SHA256SUMS' or '__pycache__' in path.parts or path.suffix == '.pyc' or path.name == '.DS_Store':
            continue
        out[rel] = path
    return out


def verify_checksums() -> None:
    checksum_path = ROOT / 'SHA256SUMS'
    if not checksum_path.exists():
        fail('SHA256SUMS is missing')
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            digest, rel = line.split('  ', 1)
        except ValueError:
            fail(f'invalid checksum line: {line}')
        declared[rel] = digest
    actual = eligible_files()
    if set(declared) != set(actual):
        missing = sorted(set(actual) - set(declared))
        extra = sorted(set(declared) - set(actual))
        fail(f'checksum file set mismatch; missing={missing[:5]} extra={extra[:5]}')
    for rel, path in actual.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if declared[rel] != digest:
            fail(f'checksum mismatch: {rel}')
    ok(f'SHA-256 checksums for {len(actual)} files')


def verify_installed() -> None:
    home = Path.home()
    canonical = home / '.agents' / 'skills' / 'human-reasoning'
    compat = home / '.codex' / 'skills' / 'human-reasoning'
    if not (canonical / 'SKILL.md').exists():
        fail(f'missing canonical installed skill at {canonical}')
    if not compat.exists() and not compat.is_symlink():
        fail(f'missing compatibility path at {compat}')
    try:
        if compat.resolve(strict=True) != canonical.resolve(strict=True):
            fail('compatibility path does not resolve to canonical skill')
        if ROOT.resolve(strict=True) != canonical.resolve(strict=True):
            fail('doctor --installed is not running from the canonical installed copy')
    except FileNotFoundError as exc:
        fail(f'installed path is broken: {exc}')
    version = (canonical / 'VERSION').read_text(encoding='utf-8').strip()
    if version != '2.1124':
        fail(f'unexpected installed version: {version}')
    ok(f'canonical install {canonical} and compatibility symlink {compat}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate Human Reasoning Bridge v2.1124.')
    parser.add_argument('--installed', action='store_true', help='also verify user-level installation paths')
    parser.add_argument('--skip-checksums', action='store_true', help='skip SHA256SUMS validation')
    args = parser.parse_args()

    verify_skill()
    tracks, passes = verify_matrix()
    final_hash = verify_iterations(tracks, passes)
    verify_tests(tracks)
    if not args.skip_checksums:
        verify_checksums()
    if args.installed:
        verify_installed()
    print(f'ALL STATIC CHECKS PASSED — final chain {final_hash}')


if __name__ == '__main__':
    main()
