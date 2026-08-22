#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'iterations' / 'iteration-log.json'

def canonical_hash(record: dict) -> str:
    payload = {k: v for k, v in record.items() if k != 'chain_hash'}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

ledger = json.loads(LEDGER.read_text(encoding='utf-8'))
records = ledger['iterations']
assert len(records) == 1124
previous = '0' * 64
pairs = set()
for expected, record in enumerate(records, 1):
    assert record['iteration'] == expected
    assert record['previous_hash'] == previous
    assert record['chain_hash'] == canonical_hash(record)
    previous = record['chain_hash']
    if expected > 100:
        pairs.add((record['track_id'], record['pass_id']))
assert len(pairs) == 1024
assert pairs == {(t, p) for t in range(1, 33) for p in range(1, 33)}
assert previous == ledger['final_chain_hash']
print(f"PASS: 1124 records; 32×32 coverage; final chain {previous}")
