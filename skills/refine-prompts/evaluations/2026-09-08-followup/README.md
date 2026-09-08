# Refine Prompts: known-issue follow-up

## Outcome

Resolve the three specific known issues from the [previous evaluation](../2026-09-08/README.md) after the user explicitly authorized continued work. All three scored reviewers confirm the targeted contracts in both source and actual output. Final scores are **9.530, 9.350, and 9.375 / 10**; mean **9.418**, minimum **9.350**. Five paired reviewers prefer the revised package by a slight margin; none reports a blocking regression.

These are sampled agent judgments, not a calibrated measurement of model capability or downstream task success. The earlier evaluation remains historical evidence; its listed defects are superseded only to the extent documented here.

## Resolved issues and counterexamples

| Issue | Source correction | Observed evidence |
| --- | --- | --- |
| Diagnostic-ready versus provisional contradiction | Define readiness once against prerequisites of the next deliverable; reference that rule from discovery and align fixtures | Cases 12/17 produce bounded diagnostic prompts without pretending to establish causes; 28 remains provisional for missing-log final selection and preserves the ban on diagnostic substitution |
| Missing verification in conditional implementation | Require changed artifact/behavior, relevant check and actual-result reporting inside each execution branch | Cases 11/25/29 include affected-layout and user-journey checks; design branches check their own artifacts and describe future implementation tests as proposed |
| Optional resources turned into prerequisites | Keep optional budget, staffing and timing in conditional guidance without placeholders/questions; preserve binding-input requirements | Case 2 asks for product, audience and outcome without resources; 27 permits an explicitly rough scenario estimate; 30 blocks an exact staffing commitment without confirmed schedule, workload and capacity |
| Retained unconditional question examples | Condition support and constraint-priority examples on whether evidence is required and questions are permitted | Case 31 preserves the exhaustive-report/ten-second conflict without questions or unauthorized constraint relaxation; Chinese contrast checks reproduce this boundary |

The earlier case 17 output was already useful; the fix is the governing-rule/fixture inconsistency, not a claim of newly improved behavior on an already-correct response.

## Scope and method

- Update `SKILL.md`, `references/need-discovery.md`, and `test-prompts.json`; preserve the Astra profile, interface metadata, explicit-invocation policy, and existing uncommitted work
- Preserve before, preliminary candidate, and final source contents/hashes in [source-snapshots.json](source-snapshots.json)
- Complete one targeted revision followed by narrow corrections identified in an independent [static audit](static-review.md); that audit refers to the preliminary candidate, called `after` at the time and stored as `candidate1` in the snapshot file
- Generate 30 preliminary and 31 final English responses using two generation agents; provide only source instructions and input prompt fields, not expected answers, scores or output files from earlier runs
- Reuse the frozen prior candidate's 27 outputs for paired comparison; verify all 27 common input prompts are unchanged
- Treat new cases 28–31 as contrast coverage, not comparative performance gains
- Use the same nine-dimensional weights and three primary independent reviewers; reverse reading order for one scored reviewer and add two qualitative paired reviewers for close results
- Keep the 9.0 score target out of reviewer instructions; recompute totals from dimension rows using exact decimal arithmetic
- Recognize that generation and review agents retain their own earlier turn context; this is not a blinded randomized experiment, and the second generation pass is not an independent seeded trial

## Final scores

| Dimension | Weight | Judge 1 | Judge 2 | Judge 3 |
| --- | ---: | ---: | ---: | ---: |
| Supported intent discovery and context recovery | 20 | 9.5 | 9.5 | 9.4 |
| Evidence fidelity and uncertainty calibration | 15 | 9.6 | 9.5 | 9.5 |
| Clarification efficiency and usability | 10 | 9.6 | 9.3 | 9.4 |
| Task-relevant Astra adaptation and model claim accuracy | 15 | 9.5 | 9.3 | 9.3 |
| Actionable deliverables and acceptance criteria | 10 | 9.6 | 9.5 | 9.6 |
| Scope, authority, and adversarial input boundaries | 10 | 9.6 | 9.4 | 9.6 |
| Observed behavioral performance | 10 | 9.6 | 9.4 | 9.4 |
| Concision and information architecture | 5 | 8.9 | 8.4 | 8.3 |
| Package validity and maintainability | 5 | 9.6 | 9.0 | 9.2 |
| Weighted total | 100 | 9.530 | 9.350 | 9.375 |

Read [scores.json](scores.json) for exact arithmetic inputs, totals, coverage and acceptance. The numerical gate passes for every primary reviewer, all three original contracts are resolved in the sampled cases, and paired review reports no blocking regression. The slight margins do not establish statistical significance.

## Verification

- Pass skill-creator `quick_validate.py`, `git diff --check`, YAML/JSON parsing, package naming and explicit-invocation checks
- Resolve runtime and evaluation relative links, including the readiness-rule heading target
- Verify 31 unique sequential fixture IDs and complete final English output coverage
- Verify the final runtime source bytes against the recorded snapshot hashes
- Complete three final Simplified Chinese contrast checks: usable conditional diagnosis, missing-log final selection, and an unresolved summary conflict with questions forbidden
- Confirm the Chinese prompts preserve no-questions instructions and do not invent source contents, diagnoses, vendor facts or constraint approval
- Keep raw Chinese outputs outside the English-only package at `/tmp/refine-astra-followup-20260908/chinese-smoke.md`
- Do not execute underlying marketing, vendor, implementation, staffing or design tasks; no real purchase, publication, model API benchmark, or runtime integration is claimed
- Make no Git commit or push, global skill synchronization, or configuration change

The fixture `expected` fields remain semantic review criteria, not executable assertions. All 31 outputs were reviewed; this is not a claim that every response is flawless or every generalization is proven.

## Remaining evaluation limits

- Observe a weaker current-market-fact verification clause in case 2: it defers some verification to execution rather than explicitly requiring evidence before the plan relies on those claims
- Observe a mild input burden in case 25: the prompt can imply the user already knows what prevents decisions, although that cause may itself need investigation
- Observe repeated interpretation paragraphs in some simple cases; instruction length and output brevity remain imperfectly balanced
- Retain limitations from single-generation, author-designed, batched fixtures, shared-model review, limited adversarial/language coverage, and absence of downstream task execution

These are residual output-quality limitations rather than evidence that the three targeted contracts remain unresolved. No guarantee of perfect prompts or 100% model utilization is made.

## Evidence

- Read the [fixed protocol](protocol.md) and [reviewer rubric](judge-rubric.md)
- Read [before outputs](before-outputs.md), [preliminary cases 1-15](candidate1-outputs-a.md), and [preliminary cases 16-30](candidate1-outputs-b.md)
- Read final [cases 1-15](final-outputs-a.md) and [cases 16-31](final-outputs-b.md)
- Read scored reviews [1](review1.md), [2](review2.md), and [3](review3.md)
- Read qualitative paired reviews [4](pair4.md) and [5](pair5.md)
