# Iteration Method

## Release arithmetic

```text
Preserved base: 100 rounds
New matrix:     32 asymmetry tracks × 32 refinement passes = 1024 rounds
Total:          1124 rounds
```

## Why a matrix

Repeating a generic “improve the prompt” instruction 1024 times would create performative iteration. The matrix forces orthogonality:

- **Rows** represent materially different human–AI asymmetries.
- **Columns** represent different ways a requirement can fail: boundary, scope, evidence, provenance, reality contact, causal mechanism, power, values, responsibility, memory, calibration, prompt stability, evaluation, integration, and minimality.
- **Each cell** contains one primary defect, one concrete change, one observable acceptance condition, and target files.

The matrix does not prove optimality. It creates a reviewable search surface and makes omissions visible.

## Preservation rule

The first 100 records in `base-v1.100.json` and `iteration-log.json` are byte-for-byte equal at the JSON object level, including their original hashes. The first new record uses the original final hash as its `previous_hash`:

```text
v1.100 final: 324aec2e67886ba25b8f36b51b8df53009531ea9f1cef9aa6a9f06389704c493
v2.1124 final: 85564233f6c04f1fa508b03366d19e33fe8f5dc6e70802ec4196d7fd62ab232c
```

## Hash rule

For each record:

1. Remove only the `chain_hash` field.
2. Serialize the remaining object as canonical JSON with sorted keys, UTF-8, and separators `,` and `:`.
3. Compute SHA-256.
4. Store the result as `chain_hash`.
5. Use it as the next record’s `previous_hash`.

`scripts/verify_iterations.py` and `scripts/doctor.py` independently recompute the chain and the 32×32 coverage.

## What “iteration” means

An iteration is a specification-level behavioral mutation. It is **not** automatically:

- a new model training run;
- a blind A/B test;
- a statistically independent sample;
- evidence that the later version is better in every host;
- a claim that quantity itself produces quality.

Real behavior must be evaluated in the target host using `evals/` and scored with `references/eval-rubric.md`. Static checks prove integrity of the artifact and test definitions, not live cognitive performance.
