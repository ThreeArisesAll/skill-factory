# Source-only consistency audit

The revision resolves the central readiness contradiction at the rule level and adds meaningful boundary fixtures. Two retained question directives still deserve narrow qualification so the new central rule is applied consistently. This is a static review only: no performance scores, behavioral pass claims, or downstream execution claims are assigned.

## Scope and verification

Compared `before` and `after`, including SKILL.md, both references, metadata and fixture expectations. No other agents, reviews or behavioral output packets were inspected. No source was edited. Parsed both YAML frontmatter/metadata and JSON fixture files, checked unique fixture IDs (27 before, 30 after), resolved relative Markdown links, and confirmed the new `readiness-rule` anchor exists. These structural checks passed.

## Confirmed source improvements

- **Readiness has one governing definition.** `after/SKILL.md:38` defines materiality against the next requested deliverable; lines 48–57 distinguish a feasible conditional/diagnostic artifact from a missing-evidence finding or final selection. The discovery reference now points back to this rule instead of separately making no-questions requests automatically provisional. The result-heading rule and self-check also refer to prerequisites of that next deliverable
- **Missing evidence cannot be erased by changing the artifact.** The provisional row explicitly prohibits replacing the requested result with a diagnostic plan merely to change its label. Required-source handling remains intact. Fixture 28 tests a final vendor decision based on absent logs, forbids diagnostic substitution, and preserves no questions. This is an important counterexample to fixture 17's intentionally bounded assessment
- **Optional resource gaps are separated from binding constraints.** The per-gap fallback remains, while line 57 and the self-check forbid redundant optional resource placeholders/questions. Fixture 2 now expects product/audience/objective questions and conditional resource guidance; fixture 27 remains a scenario estimate; new fixture 30 requires provisional handling of an exact staffing commitment with assumptions forbidden
- **Conditional implementation must carry verification.** `after/SKILL.md:76` requires each execution branch to identify changed artifact/behavior, relevant checks and evidence; webpage branches include affected layout and user journey, and blocked checks stay unverified. Fixture 11 now requires that behavior, while fixture 29 adds a fresh missing-mockup, dual-delivery-stage example with no publishing
- **Fixture 12 now distinguishes a diagnostic plan from an evidence-based diagnosis or intervention choice.** That is a more precise expectation than treating every unknown support cause as a blocker, and it aligns with the new readiness table

## Remaining actionable consistency findings

### 1. Qualify the support-question calibration example

Location: `after/references/need-discovery.md:44`

The example still says that if a user suggests a bot for support overload, ask which work consumes the most effort. Unlike the central rule, it does not condition that question on the next deliverable requiring the answer. Under updated fixture 12, the next deliverable may legitimately be a bounded diagnostic plan; under fixture 17, questions are prohibited. The surrounding general rules can resolve this, but an unconditional example is an avoidable competing instruction for the precise cases the revision is fixing.

Suggested narrow correction: make the example apply when a diagnosis or intervention decision requires that evidence and questions are permitted. Explicitly say that a diagnostic-plan prompt can instead identify that evidence as something to inspect later. No new workflow is needed.

### 2. Qualify the conflicting-constraints question directive

Location: `after/references/need-discovery.md:37`

The conflict rule still says to preserve both requirements in a provisional prompt and ask which takes precedence. The updated no-questions handling elsewhere says to state the limitation without requesting information. This is a retained local inconsistency, not a newly introduced regression. A conflict combined with no questions should remain provisional and preserve both constraints, but must not force a question.

Suggested narrow correction: ask which requirement governs only when questions are allowed; otherwise expose the unresolved priority and permit only independent work. This would align the calibration rule with SKILL.md's existing copied-selector behavior.

## Wording and coverage observations

- `after/SKILL.md:76` says a design-only branch specifies proposed acceptance checks “without running them.” Read in context, this appropriately excludes implementation tests. It could be clearer that this does not prohibit inspecting a produced design artifact for consistency with the supplied mockup. A short distinction between checking the design artifact and executing future implementation acceptance would prevent an overbroad interpretation; no demonstrated behavior failure is claimed
- The optional-resource exception uses “unless an explicit commitment depends on them.” The materiality rule above is broader and correctly covers any hard constraint. A future fixture should exercise a binding feasibility requirement that is not phrased as an exact commitment, such as choosing a plan that must fit a fixed but undisclosed capacity ceiling. This would check that the model follows materiality rather than treating all resource questions as forbidden
- Fixture 17 now requires copy-ready conditional assessment, while fixture 28 protects an explicitly requested final decision. That is a sound paired boundary. A fresh ambiguous support request should also be observed to ensure the agent does not select a diagnostic deliverable solely to obtain a ready label; fixture expectations alone cannot establish this
- The new execution clause replaces the previous compact sentence about authorized scope, completion and genuine blockers. Those concepts remain elsewhere in the entrypoint, readiness rule and Astra profile, so no concrete loss of authority protection is established. The scored behavior review should still check a non-Astra execution request because that target does not read the Astra profile

## Behavioral evidence still required

Observe the revised package on at least the changed or boundary cases 2, 11, 12, 17, 28, 29 and 30, while retaining 3/10 for absent source material, 4/19 for exact strings, 24 for current-input versus template status, and 27 for conditional resources. Check the literal prompt body as well as its heading: a provisional label cannot compensate for a fabricated recommendation, and a ready label is appropriate only if the actual next deliverable is feasible. Verify both branches of case 29 preserve their distinct acceptance behavior. This audit does not predict those outcomes.

The source changes are coherent overall and target the known issues without changing the refinement-only contract. The two question directives above are the remaining narrow consistency fixes identified here.
