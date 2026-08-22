---
name: solve-from-first-principles
description: Solve ambitious, high-uncertainty, cross-disciplinary problems by deriving constraints from first principles, using stretch targets to expose architectural limits, modeling the whole system, challenging inherited requirements, and selecting rapid falsifiable experiments. Use when a goal appears impossible, a mature system is stuck, costs or cycle times must fall dramatically, scale must increase radically, disciplines or supply chains are tightly coupled, or incremental optimization is no longer credible.
---

# Solve From First Principles

Turn an intimidating goal into a measurable system of constraints, architectural choices, and reality-tested next moves. Apply the reasoning discipline associated with first-principles engineering; do not imitate any person's voice, opinions, confidence, or persona.

## Operating stance

- Seek truth over consensus. Label observations, calculations, assumptions, and hypotheses separately.
- Treat physical laws, mathematics, and reproducible evidence as hard constraints. Treat safety, legal, ethical, contractual, and interface obligations as real constraints unless they are legitimately changed.
- Treat conventions, inherited requirements, organizational habits, and vendor assumptions as challengeable. Trace each to its source before accepting it.
- Optimize the mission and end-to-end system, not a visible component or local metric.
- Use ambition to reveal necessary architecture changes. Never use it to fabricate feasibility or certainty.
- Prefer a fast, reversible test that can disprove an idea over a long argument that protects it.

## Workflow

### 1. Define the mission contract

State the desired outcome in one sentence. Record:

- the measurable target and deadline;
- the current baseline and gap;
- the unit of value, cost, time, scale, or reliability that matters;
- available resources and explicit scope boundaries;
- unacceptable failure modes.

Ask only for missing information that would materially change the approach. Otherwise proceed with labeled assumptions and state their impact.

Complete this step when success and failure can be distinguished with evidence.

### 2. Build a constraint ledger

Decompose the claimed impossibility into atomic constraints. For each constraint, record its type, evidence, confidence, consequence, and whether it is fixed or challengeable.

Use these types:

- physical or mathematical limit;
- measured empirical behavior;
- economic or resource limit;
- safety, legal, ethical, or contractual obligation;
- dependency or interface constraint;
- policy, convention, or historical choice.

Derive lower bounds from raw quantities where possible. Show units and order-of-magnitude calculations. Compare the theoretical or empirical floor with the current baseline; the difference is the redesign space.

Complete this step when every major blocker is tied to evidence or clearly labeled as an assumption.

### 3. Delete before optimizing

Process every material requirement in this order:

1. Identify its source and the outcome it protects.
2. Test whether the outcome still matters.
3. Delete the requirement or component when its protected outcome can be preserved without it.
4. Simplify what remains.
5. Shorten feedback and delivery cycles.
6. Automate only the stable remainder.

For a contested deletion, define the cheapest safe test, rollback, and failure signal. A faster version of an unnecessary step remains waste.

Complete this step when each surviving requirement has a named justification.

### 4. Use a stretch target as a diagnostic

Compare three levels:

- current baseline;
- ambitious target;
- credible lower bound.

Ask what must be structurally different for the ambitious target to work. Identify which assumptions, interfaces, manufacturing methods, business rules, or architectures would have to change. Treat the target as a probe, not a promise. Say directly when a hard constraint makes it impossible.

Complete this step when the target has exposed specific architectural changes or a proven limiting bound.

### 5. Model the whole system

Map the flows of matter, energy, information, money, time, and decisions that affect the mission. Locate:

- bottlenecks and queues;
- tight couplings and shared dependencies;
- feedback loops and delayed effects;
- failure propagation and recovery paths;
- supply, manufacturing, software, organizational, and business-model interactions;
- local improvements that damage end-to-end throughput.

Rank bottlenecks by sensitivity: estimate how much the mission metric changes when each one improves.

Complete this step when the dominant system constraint and its important second-order effects are explicit.

### 6. Generate competing architectures

Produce at least three materially different paths when the problem warrants it:

- a minimal-change path;
- a structural redesign;
- a radical path near the credible lower bound.

Estimate each with ranges, units, dependencies, reversible and irreversible decisions, and the assumptions carrying the most risk. Include a pre-mortem: name the most plausible way each path fails.

Choose based on mission leverage, evidence, reversibility, and learning speed rather than novelty.

Complete this step when the recommendation survives comparison with credible alternatives.

### 7. Find truth fast

Rank uncertainties by decision leverage, uncertainty, and cost of being wrong. For the highest-ranked uncertainty, design the smallest real-world experiment that can falsify the proposal.

Specify:

- hypothesis and predicted observation;
- test setup and required resources;
- metric and pass/fail threshold;
- timebox;
- safety limit, stop condition, and rollback;
- decision unlocked by each result.

Prefer measured behavior, prototypes, and production-like tests. Do not confuse activity, a demo, or positive anecdotes with validation.

Complete this step when the next experiment can change a consequential decision.

### 8. Build the critical path

Convert the selected architecture into the smallest sequence that retires the largest risks first. For each action, name the deliverable, owner when known, dependency, timebox, and exit criterion. Keep irreversible commitments late and feedback loops short.

Recommend one highest-information next move, plus at most two immediate follow-ons. After new evidence arrives, update the constraint ledger and re-plan instead of defending the original answer.

Complete this step when execution can start without guessing what done means.

### 9. Communicate the decision

Lead with the recommendation and the hardest truth. Scale the response to the problem; do not force a long template onto a simple question.

For substantial problems, use this order:

1. Mission and baseline gap
2. Hard constraints and challengeable assumptions
3. Dominant system bottleneck
4. Competing architectures and recommendation
5. Critical calculations and confidence
6. Falsifying experiment
7. Critical path and next move

Attach one of these labels to consequential claims:

- **Observed**: directly measured or sourced.
- **Calculated**: derived from shown inputs.
- **Assumed**: necessary but unverified.
- **Hypothesized**: testable causal belief.

End with the evidence that would most likely change the recommendation.

## Guardrails

- Preserve safety, legality, ethics, reliability, and human dignity while pursuing extreme performance.
- Challenge systems and assumptions, not people's worth. Do not substitute pressure or charisma for engineering evidence.
- Avoid false precision. Use ranges and sensitivity analysis when inputs are uncertain.
- Do not hide infeasibility. Return the binding constraint and the closest feasible target.
- Do not optimize a proxy unless its causal connection to the mission metric is explicit.
- Do not present a stretch goal, scenario, or hypothesis as a forecast or commitment.
