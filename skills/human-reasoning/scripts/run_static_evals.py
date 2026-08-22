#!/usr/bin/env python3
"""Validate deterministic fixtures and emit the live-host evaluation checklist.

This script does not claim to evaluate a model. A live evaluation requires a
captured run in the target Codex/ChatGPT host and rubric scoring.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument('--summary-only', action='store_true')
args = parser.parse_args()

subprocess.run([sys.executable, str(ROOT / 'scripts' / 'doctor.py')], check=True)
behavior = json.loads((ROOT / 'tests' / 'behavior-cases.json').read_text(encoding='utf-8'))
anti = json.loads((ROOT / 'tests' / 'anti-anthropomorphism-cases.json').read_text(encoding='utf-8'))
trigger = json.loads((ROOT / 'tests' / 'trigger-cases.json').read_text(encoding='utf-8'))

print('\nLIVE-HOST EVAL INVENTORY')
print(f"  trigger: {len(trigger['positive'])} positive / {len(trigger['negative'])} negative")
print(f"  behavior: {len(behavior)} track cases")
print(f"  anti-anthropomorphism: {len(anti)} cases")
print('  rubric: references/eval-rubric.md')

if not args.summary_only:
    for case in behavior:
        print(f"\n{case['id']} [{case['mode']}] {case['prompt']}")
        print('  must: ' + '; '.join(case['must']))
        print('  must not: ' + '; '.join(case['must_not']))
        print('  observable: ' + case['observable'])

print('\nStatic fixtures passed. Run captured model executions separately; do not report this output as a live model score.')
