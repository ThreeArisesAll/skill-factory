---
name: model-router
description: Route executable Codex tasks to suitable models while controlling delegation cost and implementation complexity. Use for implementation, debugging, repository investigation, reviews, maintenance, creative work, design, copywriting, and Computer Use. Honor explicit user opt-outs; pure conversation is exempt.
---

# Model Router

## Entry and ownership

This file is the single source of routing policy. Project and agent configuration files reference it rather than restating its categories or exceptions. Resolve its path from the repository root, including when the working directory is a subdirectory.

Route once per executable user task, before substantive work. Reading this skill and minimal context needed to classify the task are allowed first. Reuse the decision for follow-ups on the same task; reconsider only when scope or evidence changes. Pure conversation and explanations that require no executable work are exempt.

If you are a delegated child or receive `MODEL_ROUTER_DELEGATED`, execute your bounded assignment directly, apply the engineering gate below, and return blockers to the lead. Do not route again or spawn grandchildren.

The lead owns integration, verification, and final delivery. Routing does not change the active lead model. Never create a separate user-visible task to route work or silently modify model defaults while executing ordinary tasks.

## Choose a route

Subject to higher-priority instructions, decide in this order:

1. Honor explicit user skill or routing opt-outs and model choices. An opt-out bypasses this routing workflow, including mandatory delegation; continue under the user's task and repository requirements.
2. Identify any Required Astra work below. Give only that portion to Astra, with the specified ownership and unavailable-model rules.
3. For the remaining work, decide whether a concrete independent unit justifies delegation; otherwise execute inline. Select its model and initial effort from Ordinary routing.
4. Define acceptance and necessary checks before implementation, then pass the bounded Delegation contract when assigning a child.

### Required Astra work

Assign the following work to a `gpt-6-astra` child agent (`astra-specialist`, initial effort `medium`):

- Creative ideation, visual/product/interaction design, drafting or substantively rewriting copy, and Computer Use that operates browser or native-app interfaces. Category membership is sufficient justification; no failed attempt or difficult-bug evidence is needed.
- Difficult root-cause or architectural code reasoning justified by existing evidence, such as conflicting observations, an unresolved root cause after investigation, or a concrete difficult invariant. Task size, file count, or the word "architecture" alone is insufficient. Do not require a failed lower-model attempt when difficulty is already established.

This assignment is mandatory even for small tasks or when the lead is already Astra. It takes precedence over cost optimization and ordinary inline preferences. Implementing an already specified visual change without making new design decisions is ordinary engineering; mechanical formatting and factual documentation maintenance are not creative copywriting. Merely discussing Computer Use is not operating a UI.

For mixed tasks, give Astra ownership of the affected work and route separable engineering work normally. Do not perform the mandatory portion inline or send it to a cheaper model to save overhead. The lead should continue useful non-overlapping integration or verification work where available; if higher-priority runtime constraints prevent delegation, report the constraint rather than silently replacing the required Astra child. If Astra or required tools are unavailable, keep that portion pending and report what is missing.

Under that precedence, a non-Astra child discovering required work, including during read-only work, pauses only that portion and returns its scope, evidence, and necessary context to the lead for Astra assignment. Continue other authorized independent work without spawning children. Ordinary uncertainty alone is a blocker to report, not automatic evidence that Astra is required.

### Ordinary routing

Assess actual complexity, uncertainty, failure impact, context required, and repetition. Optimize total work, including dispatch overhead and potential rework. The model ordering below is a user preference, not a verified price formula.

| Work                                                                                                                                                        | Preferred model | Initial effort | Custom agent  |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | -------------- | ------------- |
| Bounded repo search, log extraction, formatting, straightforward docs, mechanical edits                                                                     | gpt-5.6-luna    | high           | luna-explorer |
| Main development, routine implementation/refactoring, ordinary bugs, integration, cross-module implementation, release evidence assembly, simplicity review | gpt-6.1-sol     | high           | sol-engineer  |

When neither Required Astra work nor a user-mandated model applies, INLINE is preferred for trivial work, tightly coupled tasks, when the current model already fits, or when delegation overhead exceeds its benefit. Do not manufacture parallel tasks to use cheaper models. Delegate only a concrete independent unit while the lead has useful non-overlapping work. For substantial independent work, this skill explicitly instructs delegation to the suitable model above.

Use only capabilities exposed by the current runtime. When custom agent selection is supported, select the named role. Otherwise use explicit `model` and `reasoning_effort` arguments with the mapping above. If full-history forks disallow model overrides, use a minimal-context fork (for example `fork_turns="none"`) and pass the necessary facts. Never omit model selection and assume a child is cheaper. Do not invent unsupported tool parameters or model aliases.

If an ordinary routing choice is unavailable, report the limitation and continue inline only when reliable and neither required Astra work nor a user-mandated model is affected. Otherwise keep the affected portion pending and report what is missing. Instant and GPT-6 Pro Chat are Chat preferences, not aliases for these Codex models. Do not claim to invoke them or that Astra provides a GPT-6 Pro Chat review. If that review is explicitly required, prepare the handoff and identify the remaining Chat step.

For nontrivial execution, state one concise routing sentence in the user's language. Name the applicable category or the concrete evidence for difficult reasoning. Escalate with evidence and attempts so far; avoid repeated blind retries. Raise effort only for demonstrated reasoning needs; do not default to max/ultra.

## Delegation contract

Include `MODEL_ROUTER_DELEGATED`, objective, allowed files or read-only scope, acceptance criteria, relevant evidence, model/effort, and the engineering gate from this skill. Send minimum sufficient context. Keep write ownership disjoint; preserve existing and parallel edits. Request changed files, verification results, and unresolved issues. Workers must return uncertainty to the lead rather than recursively delegating. This policy does not expand external-action authorization.

## Minimal Engineering Gate

Apply to every implementation, inline or delegated. Before implementation, reuse the user's and repository's acceptance criteria; where absent, define the minimum observable result and necessary checks. Do not add a confirmation gate or weaken criteria to fit the implementation. Consider broadly, modify narrowly.

1. DELETE / REUSE / SIMPLIFY: inspect current code and determine the smallest change meeting those criteria. Reuse existing mechanisms before adding new ones.
2. IMPLEMENT: ordinary bug fixes should prefer 1-3 existing files, no new dependency, and no unrelated refactor. This is a preference, not a correctness limit; explain concrete necessity when exceeding it, without creating an approval gate.
3. Every new abstraction, state, dependency, fallback, retry, cache, or test infrastructure needs a current requirement, observed failure, or concrete invariant. Hypothetical future flexibility is insufficient. Generalize only when at least two current concrete uses justify it, or an explicit current contract requires the abstraction.
4. HARDEN only at real input/external failure boundaries or for demonstrated risks. Expose broken internal invariants rather than silently hiding them. Preserve necessary existing safety and correctness checks.
5. Verify the agreed observable result, reproduced bugs, and critical affected invariants with the necessary and repository-required checks; do not impose a universal test suite. UI changes require evidence of the actual effect; configuration changes require evidence of actual loading. Follow repository restrictions on verification methods: in IBL, do not run browser tests for UI changes; complete permitted checks and deliver a human verification checklist covering affected behaviors and states. Mark visual acceptance as pending until human evidence is available; do not present static checks as visual proof or block the implementation handoff solely on that pending evidence. Mark other checks not run and missing evidence explicitly. Avoid speculative exhaustive matrices, implementation-mirroring tests, and new tests for reversible low-impact edits. High-reliability requirements still govern their actual scope.
6. COMPRESS once: inspect the diff for unnecessary additions; delete or simplify only when correctness and readability remain intact. This pass must not become another hardening/refactoring round. A concrete correctness defect returns to the solve phase. Recheck affected behavior after changes.
7. STOP when acceptance and required checks pass. Report remaining unverified external evidence honestly. Record unrelated debt briefly only if useful; do not implement it.

Use a bounded sol-engineer simplicity review only when independent review has concrete value and the lead has useful parallel work; otherwise perform the pass inline. No mandatory reviewer swarm or extra review loop.

## Policy verification

Use [behavioral acceptance cases](tests/behavioral-cases.md) when evaluating policy changes. TOML parsing, path resolution, and prompt inspection establish configuration evidence only. Actual delegation, handoff, and stopping behavior require execution traces; do not report unexecuted cases as passed.
