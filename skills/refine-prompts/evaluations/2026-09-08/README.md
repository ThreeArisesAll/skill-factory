# Refine Prompts: Astra and intent-discovery evaluation

> Historical evaluation: the user subsequently authorized a [known-issue follow-up](../2026-09-08-followup/README.md). Its current evidence and resolved contracts supersede the three targeted limitations recorded below.

## Result

Accept the third candidate after three editing rounds. Final independent weighted scores are **9.435, 9.185, and 9.265 / 10**; mean **9.295**, minimum **9.185**. All three exceed the predeclared 9.0 threshold without rounding. Five paired reviewers prefer the final candidate by a slight margin, with no blocking regression reported. Stop at the requested three-round limit; retain the limitations below rather than starting a fourth round.

These are subjective agent assessments of sampled outputs, not official benchmarks, guaranteed correctness, or evidence of using 100% of a model's capability.

## Scope and baseline

- Improve the repository package at `skills/refine-prompts`, preserving its existing explicit-invocation policy
- Use the already modified working-tree package as the starting baseline; do not attribute its pre-existing Astra/discovery work to this run
- Preserve source contents and SHA-256 hashes in [source-snapshots.json](source-snapshots.json), covering the baseline and all three candidates
- Use frozen file snapshots instead of commits to preserve existing uncommitted work; make no commit, push, global installation change, or configuration change
- Verify that the separate installation at `/Users/threeaa/.agents/skills/refine-prompts` is not linked to this repository; this run does not synchronize it

## What changed in this run

- Add evidence-based recovery of short referents and implied practical outcomes, while retaining unknown causes and consequential alternatives
- Separate missing task direction from evidence an authorized diagnostic task is intended to gather
- Preserve business goals, delivery stages, fixed decisions, literal strings, and source-data boundaries
- Reduce unnecessary material placeholders and future-stage questions; specify what can proceed before an unresolved choice is answered
- Distinguish missing current inputs from explicitly requested reusable template inputs
- Compose task-relevant Astra instructions around outcomes, evidence, constraints, completion and proportionate verification
- Expand the English semantic fixture set from 19 to 27 cases and update the interface description/default prompt

## Method

Use the fixed [protocol](protocol.md) and [judge rubric](judge-rubric.md). Seven separate generation agents produce actual prompt-refinement responses; they receive source instructions and input prompts without expected answers, scores, or previous candidate outputs. Five independent reviewers assess outputs; three assign nine-dimensional scores and two perform additional pairwise reviews. Reviewers are not given the target score. One scored reviewer and one pair reviewer read the versions in reverse order. The same primary reviewers retain their own earlier review context for within-reviewer comparisons, so this is not a fully blinded randomized study.

Compare eight baseline outputs with corresponding first-candidate outputs; additional first-candidate cases establish coverage, not comparative gain. Round two compares 24 common cases and adds three transfer probes. Round three compares the same 27 inputs on both versions. Each candidate has one English generation per case; prompts are evaluated in batches, not independent model sessions per case. No no-skill control was run. Close pairwise results receive two additional reviewers for rounds two and three; round one already fails the numerical acceptance gate and is not accepted as final.

Recompute scores from the individual dimension rows, respecting each report's X/Y column order, using exact decimal arithmetic. The raw [scores.json](scores.json) includes all dimensions, totals, coverage, and limitations. Expected fixture prose is a semantic review guide, not an executable assertion or proof of a pass.

## Iteration results

| Round | Judge 1 | Judge 2 | Judge 3 | Mean | Minimum | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 9.155 | 8.985 | 9.030 | 9.057 | 8.985 | Below threshold; correct unsupported goal/stage narrowing and redundant gaps |
| 2 | 9.330 | 9.060 | 9.150 | 9.180 | 9.060 | Numeric threshold met; use final allowed round to fix exact-label ambiguity and incorrect template status |
| 3 | 9.435 | 9.185 | 9.265 | 9.295 | 9.185 | Accept and stop; 5/5 slight paired preference, no blocking regression reported |

## Final dimensional scores

| Dimension | Weight | Judge 1 | Judge 2 | Judge 3 |
| --- | ---: | ---: | ---: | ---: |
| Supported intent discovery and context recovery | 20 | 9.5 | 9.3 | 9.3 |
| Evidence fidelity and uncertainty calibration | 15 | 9.6 | 9.4 | 9.4 |
| Clarification efficiency and usability | 10 | 9.4 | 9.1 | 9.2 |
| Task-relevant Astra adaptation and model claim accuracy | 15 | 9.4 | 9.3 | 9.3 |
| Actionable deliverables and acceptance criteria | 10 | 9.3 | 9.1 | 9.3 |
| Scope, authority, and adversarial input boundaries | 10 | 9.5 | 9.2 | 9.5 |
| Observed behavioral performance | 10 | 9.5 | 9.2 | 9.3 |
| Concision and information architecture | 5 | 9.2 | 8.5 | 8.6 |
| Package validity and maintainability | 5 | 9.1 | 8.7 | 8.8 |

## Observed improvements

- Preserve the missing marketing objective instead of assuming acquisition in case 2
- Require the missing interview while making shipping feasibility conditional, without a second capacity gate, in case 3
- Preserve `Buy` and `Place order` exactly with explicit literal boundaries in case 4
- Expose the homepage delivery stage instead of silently selecting proposal-only work in case 11
- Permit bounded diagnosis before a future implementation decision in case 12
- Prevent an unfilled priority selector from silently resolving incompatible summary requirements in case 14
- Mark metric roles as recommendations while measuring clicks and completed purchases in case 16
- Recover supplied context for a terse teacher-facing upload-message request in case 22
- Keep a quoted hostile instruction as source data in case 23
- Reject performance guarantees and retain provisional status for missing current product ideas in case 24

## Verification performed

- Pass the skill-creator `quick_validate.py` check on the final package
- Pass `git diff --check`
- Parse frontmatter and interface YAML, confirm package naming and explicit invocation, and resolve the runtime documentation's relative links
- Parse 27 uniquely numbered JSON fixtures and verify complete generated output coverage for each candidate: 24, 27, and 27 cases
- Preserve eight baseline outputs; total English generated responses across baseline/candidates: 86
- Complete two additional Simplified Chinese smoke tests on both rounds two and three; final responses preserve no-question and output-only instructions and do not fabricate causes or measurements
- Keep raw Chinese smoke outputs outside the English-only package at `/tmp/refine-astra-20260908/chinese-smoke-round3.md`; the primary scored suite is English
- Compare final runtime source bytes against the frozen third-candidate snapshot
- Do not execute the underlying marketing, implementation, design, or research tasks; no downstream success is claimed
- Do not measure a pinned API model snapshot, reasoning setting, latency, token cost, repeated-seed reliability, or actual runtime integration; no claim about these follows from prompt-generation review

## Remaining limitations

- Retain a status-contract inconsistency in case 17: a bounded diagnostic prompt is useful and can reasonably be copy-ready, while the retained fixture and a no-questions discovery statement still favor provisional labeling
- Retain a sampled omission in case 11: the final generated prompt lacks the earlier candidate's explicit layout/registration verification requirement when implementation is selected
- Retain occasional over-clarification of optional resources in case 2 and some unnecessary interpretation prose for simple inputs
- Recognize shared-model judgment bias, small paired score margins, author-designed fixtures, batch context effects, and limited unseen/adversarial coverage
- Treat English and Chinese smoke success as observed coverage rather than universal language or task reliability

If a further iteration is authorized, first unify the diagnostic-ready versus provisional rule and its fixtures, then test conditional implementation branches for required verification, and finally run repeated unseen English/Chinese prompts with a pinned model configuration. Preserve the existing score rubric and include a no-skill control and downstream task checks if measured performance gains are required.

## Evidence index

- Read [baseline outputs](baseline-outputs.md), [round 1 main outputs](round1-outputs.md), and [round 1 regression outputs](round1-regression-outputs.md)
- Read [round 2 cases 1-14](round2-a.md) and [round 2 cases 15-27](round2-b.md)
- Read [round 3 cases 1-14](round3-a.md) and [round 3 cases 15-27](round3-b.md)
- Read round 1 reviews: [judge 1](round1-judge1.md), [judge 2](round1-judge2.md), [judge 3](round1-judge3.md)
- Read round 2 reviews: [judge 1](round2-judge1.md), [judge 2](round2-judge2.md), [judge 3](round2-judge3.md), [pair 4](round2-pair4.md), [pair 5](round2-pair5.md)
- Read final reviews: [judge 1](round3-judge1.md), [judge 2](round3-judge2.md), [judge 3](round3-judge3.md), [pair 4](round3-pair4.md), [pair 5](round3-pair5.md)

## Official model guidance

Review the [official Astra model guide](https://developers.openai.com/api/docs/guides/latest-model) and [Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra), accessed on 2026-09-08. The guide supports task-specific calibration of initiative, instruction sensitivity, response style, delegation, verification and host-dependent runtime features. The latest-model URL may later change; preserve the explicit GPT-6 Astra target when maintaining this package.
