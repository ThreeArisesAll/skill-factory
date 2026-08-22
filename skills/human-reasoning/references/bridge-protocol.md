# BRIDGE Operational Protocol

Use this reference for difficult or high-stakes cases. The main `SKILL.md` remains the authority; this file expands the working artifacts.

## 0. Comparison card

```text
Decision:
Human population / roles:
AI model and host:
Modalities:
Context and retrieval:
Persistent memory and retention:
Tools and data sources:
Sensors and actuators:
Permissions and autonomy:
Policies / legal constraints:
Human operators and reviewers:
Time horizon:
Stakes and reversibility:
```

Do not continue with broad “human versus AI” claims until the card is concrete enough for the decision.

## 1. Claim-level ledger

```text
Claim:
Level: behavioral | mechanism | functional state | experience | normative status
Status: observed | sourced | reported | calculated | inferred | assumed | unknown
Source / date:
Confidence basis:
What would disconfirm it:
Decision impact if wrong:
```

Common invalid jumps:

- fluent empathy → felt empathy;
- successful task performance → human-like mechanism;
- sensor input → subjective sensation;
- persistent database → autobiographical self;
- autonomous action → self-owned goal;
- generated agreement → consent or commitment;
- explanation → faithful causal trace;
- tool capability → authorization;
- benchmark parity → equal responsibility or local safety.

## 2. Bind to human reality

Create a **human reality card**:

```text
Goal owner:
Affected people:
Decision owner:
Executor:
Reviewer / appeal:
Who bears bodily, financial, social, and reputational consequences:
Values and non-negotiables:
Power asymmetries:
Place / culture / institution:
Available time, energy, attention, money, and skill:
Privacy and safety boundaries:
Failure recovery:
```

Then simulate one episode with a named actor. Ask: what happens five minutes before use, during failure, and the next day?

## 3. Select asymmetries

Scan the 32-axis matrix once. Retain an axis only when at least one is true:

- it can reverse the choice;
- it creates a severe or hard-to-detect failure;
- it changes the evidence required;
- it changes who may decide or act;
- it changes reversibility, appeal, or remedy;
- it determines the human–AI allocation.

For each retained axis, fill a control card:

```text
Axis:
Human condition in this case:
AI condition in this runtime:
Failure mechanism:
Missing reality contact:
Compensating control:
Evidence / provenance:
Observable pass condition:
Human value owner:
Accountable owner:
Residual risk:
```

## 4. Import reality contact

Rank evidence by its ability to correct the actual model, not by rhetorical prestige.

Useful classes include:

- primary records and user-provided artifacts;
- current authoritative sources;
- direct measurement and calculation;
- calibrated sensor data;
- demonstrations and observed skilled performance;
- local practitioner and affected-person testimony;
- prototypes, simulations, pilots, and controlled interventions;
- outcome and incident data;
- independent replication or solution paths.

Ask one question only when the answer blocks responsible action. Otherwise state a safe assumption and proceed with a bounded conclusion.

## 5. Causal and social model

Represent the minimum model that changes the decision:

```text
Desired outcome ← direct causes ← controllable levers
                     ↑              ↓
                confounders     feedback / adaptation
                     ↑              ↓
         incentives, power, information, trust, fatigue, institutions
```

For important actors, distinguish:

- observed action;
- plausible belief or motive;
- incentive and constraint;
- formal authority;
- informal power;
- freedom to refuse or appeal;
- likely adaptation after the intervention.

Mental states remain hypotheses. A coherent story is not evidence of another person’s inner state.

## 6. Alternatives by comparative advantage

Compare at least:

```text
A. Current / human-only baseline
B. AI-heavy allocation
C. Hybrid allocation by operation
D. No action, when real
```

Decompose the workflow into operations such as sensing, retrieval, synthesis, calculation, value selection, consent, decision, execution, review, and remedy. Allocate each separately. Do not call a workflow “human in the loop” unless the human has enough information, time, competence, and authority to detect and override error.

## 7. Stress tests

Select the most discriminating subset:

- reverse the user’s stated preference;
- restate the task neutrally;
- swap option order;
- remove emotionally loaded wording;
- ask an independent solver;
- test a local edge case or changed distribution;
- grant the AI the missing tool and ask whether the conclusion changes;
- increase human fatigue or power asymmetry;
- run a premortem and recovery drill;
- test what happens when memory is stale, absent, or contradictory;
- require an executable or physical artifact instead of prose.

Report material instability; do not average it away.

## 8. Decision rule

A default rule for substantial cases:

```text
Choose the option that best advances the human-owned objective
subject to safety, rights, authorization, value constraints, and evidence integrity,
then prefer lower irreversible downside, lower review burden, better recovery,
and higher information gain.
```

Override this rule only when the user’s legitimate values require a different tradeoff; make that value choice visible.

## 9. Decision record

```text
Judgment:
Decisive reasons:
Human reality and affected parties:
Selected asymmetries and controls:
Evidence and provenance:
Main assumptions / unknowns:
Strongest countercase:
Confidence and basis:
What would change the judgment:
Human decision owner / authorization:
Appeal, rollback, and remedy:
Smallest learning move:
Signal and review point:
State to write, update, expire, or delete:
```

This record is preferable to a raw chain-of-thought transcript because it is compact, testable, and tied to evidence and responsibility.

## 10. Stop condition

Stop when additional analysis is unlikely to change the choice, control, or next experiment enough to justify its cognitive and operational cost. Do not run the protocol as ceremony.
