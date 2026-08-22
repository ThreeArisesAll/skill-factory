---
name: decompose-work-atomically
description: Break a user's idea, desired outcome, project, feature, change, or implementation request into scoped, ordered, verifiable atomic tasks or steps. Use when the user asks to decompose or atomize work, create a work breakdown, checklist, or implementation plan, expose dependencies or parallel work, or turn a broad vision into execution-ready tasks with acceptance criteria.
---

# Decompose Work Atomically

## Purpose

Turn an idea or intended outcome into an inspectable execution plan whose leaf tasks have clear boundaries and proof of completion. Produce the decomposition only. Do not execute tasks, edit files, or trigger external actions unless the user separately requests execution.

## Workflow

### 1. Establish the outcome contract

- Restate the target as an observable outcome, not an activity.
- Extract required deliverables, constraints, stated scope, and explicit exclusions.
- Distinguish user-provided facts from assumptions and unresolved questions.
- Preserve the user's boundary. Do not invent features, tools, legal work, market validation, release work, or other scope.
- Infer the planning horizon conservatively. Do not turn a request for a tool, feature, or change into an assumed MVP program, product strategy exercise, or full delivery lifecycle.
- Do not refine the user's audience, business model, success metric, solution category, or operating policy unless the request makes that choice necessary.
- Classify candidate work as required, optional, or excluded. Keep optional suggestions outside the required task graph.
- Ask a question only when a missing answer would materially change the task graph and cannot safely become a decision task. Otherwise proceed with a visible assumption.

### 2. Build the dependency graph

- Work backward from each required deliverable to the inputs needed to produce it.
- Add research, decision, approval, migration, verification, release, or rollback tasks only when the requested outcome actually requires them.
- Do not add conventional lifecycle work by habit. Personas, MVP scope freezes, architecture records, data-retention policies, launch plans, and status reports require a direct link to the stated outcome or constraints.
- Turn a consequential unknown into an explicit research or decision task with its own evidence and decision rule. Never hide it inside an implementation task.
- Separate work that crosses ownership, authority, system, transaction, or failure-recovery boundaries.
- Use phases only to organize the graph. A phase or milestone is never an atomic leaf task.
- Do not create a task whose only result is to restate, summarize, or report evidence already produced by other tasks unless that document is a requested deliverable.

### 3. Split until every leaf is atomic

Treat a leaf task as atomic only when all of these are true:

- It produces one primary observable result.
- Its required inputs are named or supplied by predecessor tasks.
- Its output, state change, artifact, or decision is explicit.
- Its completion condition is binary and evidence-based.
- Its dependencies are explicit.
- It can be assigned, estimated, executed, failed, retried, and reviewed independently at the plan's chosen level.
- Splitting it again would create mechanical actions with no independently useful or verifiable result.

Apply these splitting rules:

- Split hidden conjunctions such as "design and implement," "research and choose," or "build backend and frontend."
- Split production from independent approval, integration verification, deployment, or publication when they have different authority or failure states.
- Keep verification of the same result in the task's completion condition when it is merely the proof of that result. Create a separate verification task only when it is an independent gate or cross-component outcome.
- Do not create meaningless micro-steps such as opening an editor, creating an empty file, typing a command, or reading a document unless that step produces a separately useful artifact or decision.
- Do not use vague leaves such as "handle edge cases," "finish integration," "ensure quality," or "test everything." Name the exact result and evidence.

### 4. Validate the graph

- Map every requested deliverable and constraint to one or more leaf tasks.
- Remove any task that cannot be traced to a requested deliverable, a stated constraint, or a necessary prerequisite.
- Ensure each non-final output is consumed by a later task or is an explicitly requested artifact.
- Ensure dependencies are acyclic and sufficient; do not rely on unstated prerequisites.
- Place research and decisions before the work that consumes their results.
- Identify tasks that can run in parallel without inventing parallelism across shared state or unresolved decisions.
- Re-split any task whose completion could be partially true.
- Merge any task that is only a mechanical fragment of its parent and has no independent result.

## Output Contract

Write in the user's language. Prefer concrete domain terms over generic project-management language.

### Goal contract

State:

- Outcome
- Deliverables
- In scope
- Out of scope
- Constraints
- Assumptions and unresolved decisions

Omit fields that truly have no content, but never omit a material uncertainty.

### Atomic task graph

Use stable IDs such as `T001`, `T002`, and `T003`. For each leaf task provide:

| Field | Requirement |
| --- | --- |
| Task | Start with an imperative verb and name one result. |
| Inputs | Name required artifacts, facts, decisions, or predecessor outputs. |
| Output or evidence | Name the inspectable artifact, state, record, or decision produced. |
| Done when | Give a binary, evidence-based acceptance condition. |
| Depends on | List task IDs or `None`. |

Use a compact ordered list instead of a table for a very small decomposition, but retain every field above.

### Execution order

- Group ready tasks into dependency-safe waves.
- Mark genuinely parallel tasks within a wave.
- Identify decision or approval gates that block later waves.

### Coverage and gaps

- Map deliverables to the task IDs that complete them.
- List unresolved decisions, assumptions, or missing evidence that could change the plan.
- State clearly when the decomposition is provisional.
- If optional follow-up work would be useful, list it separately and do not present it as required.

## Quality Bar

Before returning the plan, confirm that:

- Every leaf has exactly one primary result.
- Every leaf has explicit evidence and a binary completion condition.
- No task silently expands the user's scope.
- No task exists merely because it is customary in a product or engineering lifecycle.
- No unknown is disguised as a fact.
- No implementation, approval, publication, or destructive action is implied to be authorized merely because it appears in the plan.
- The plan stops at useful atomicity rather than decomposing work into keystrokes.

## Example of the Atomicity Boundary

Avoid this leaf:

> Research providers, choose one, integrate it, and test the complete flow.

Prefer separate leaves:

1. Produce a provider comparison against named criteria.
2. Record the selected provider and decision rationale.
3. Implement the integration against the approved provider contract.
4. Produce end-to-end evidence for the integrated flow.

Each leaf has a distinct result, failure state, and completion proof. Do not split the implementation leaf further unless its internal parts also have independently useful outputs or cross a meaningful boundary.
