---
name: handoff-next-goal
description: "Identify the single highest-priority next development stage, express its multi-task outcome as an evidence-backed Goal Contract, create exactly one self-contained Codex thread, and activate Goal mode there. Use when the user explicitly asks to hand off or start the next development stage; do not use for handing off one atomic development task, backlog listing, document-only planning, or implementation in the current thread."
---

# Handoff Next Goal

Move a project from a completed or bounded stage into exactly one new Codex thread running in Goal mode. Select the next stage from live evidence, define its target state and authority, dispatch the Goal Contract, confirm Goal activation, and stop. Do not implement the goal in the source thread.

The contract must preserve five complete elements: **Goal + State + Constraints + Authority + Evidence**. It is an outcome contract, not a procedural checklist.

This Skill operates at a different level from a task handoff:

- A **next development stage** is a coherent target state that may require multiple atomic tasks, intermediate decisions, and successive verification layers before it reaches its terminal condition.
- A **next development task** is one bounded unit of work with one immediate delivery objective.
- Do not collapse a stage into the next atomic task merely because that task is the first likely action. Preserve the stage-level outcome and allow the Goal-mode destination to derive and execute its constituent tasks.
- This Skill is self-contained. Do not invoke, read, or reuse `$handoff-next-task`, its prompt template, or its dispatch workflow.

## 1. Establish the source boundary

- Treat this thread as the source and exactly one new peer thread as the destination.
- Interpret the user's explicit focus as a candidate goal, not as proof that it is still the live frontier.
- Carry forward only authority already granted. Creating the destination does not grant permission to commit, push, open or close issues or pull requests, merge, deploy, modify production, spend money, access credentials, communicate externally, or make unresolved product decisions.
- Do not modify project files, trackers, remote systems, or production while preparing the handoff. Read-only inspection and the one requested thread creation are allowed.
- Read every applicable `AGENTS.md` plus directly relevant `CONTEXT`, ADR, specification, plan, and ticket material before selecting the frontier.

If the request does not authorize creation of a new Codex thread and activation of Goal mode there, produce no dispatch; explain the missing authority.

## 2. Refresh the real state

Inspect the smallest sufficient set of live sources, expanding only when needed:

- repository root, branch, exact HEAD SHA, worktree status and relevant diff;
- recently completed work and its current validation evidence;
- open issues, pull requests, reviews, CI runs, blockers, assignees, milestones, and dependency relationships when they control priority;
- applicable instructions, roadmap, `CONTEXT`, ADRs, specs, tickets, relevant implementation seams, tests, failures, and TODOs;
- destination project and whether the required branch, commit, or working-tree state is reachable there.

Do not trust the old conversation, summaries, issue state, CI state, or historical test results merely because they were previously correct. Refresh mutable facts immediately before using them for selection or dispatch. Treat durable ADR and `CONTEXT` decisions as controlling until newer authoritative evidence supersedes them.

Label destination-relevant claims exactly as one of:

- `[Verified YYYY-MM-DD HH:MM TZ]`
- `[Existing evidence, not reverified this turn]`
- `[Inference]`
- `[Unknown]`

Never read, copy, or echo secret values. Refer only to the secure source or required retrieval mechanism.

## 3. Select one next development stage

Derive candidate next stages from unfinished outcomes and actual blockers. Compare only plausible candidates using:

- prerequisite and causal ordering;
- user or product value and the amount of downstream work unblocked;
- urgency and active failure risk;
- readiness, uncertainty, and evidence quality;
- boundedness, reversibility, and acceptance cost.

Select exactly one highest-priority **stage goal**: a coherent product or engineering target state that is large enough to contain multiple related development tasks when the evidence requires them, yet bounded by observable terminal conditions. It may culminate in an implementation capability, systemic repair, migration, integrated acceptance outcome, or explicit human decision that unlocks a subsequent stage. Review, re-review, audit, backlog grooming, and open-ended issue discovery are evidence activities, not stage goals.

Record only real causal dependencies. Do not turn a preferred implementation sequence into a fixed checklist, and do not substitute the first atomic task for the stage outcome. If repository evidence identifies a unique next stage, choose it and state why. If materially different stages remain tied because of unresolved product semantics, authority, or inaccessible evidence, ask one minimal blocking question and create no thread.

## 4. Build the Goal Contract

Create a self-contained launch prompt in the user's language. Preserve exact technical names, identifiers, paths, commands, and errors when translation would reduce precision. Include every section below; write `None` only when a section is genuinely empty.

```text
Goal Mode Bootstrap
- Before any investigation, planning, or implementation, call `create_goal` exactly once with `objective` set to the Task / Target State below, expanded only enough to preserve its full stage scope.
- Omit `token_budget` unless the user explicitly supplied one.
- Immediately confirm the active goal with `get_goal` when available.
- If Goal creation is unavailable or fails, stop without implementing the stage and report that Goal mode was not activated.

Task / Target State
<One sentence describing the externally meaningful stage-level target state, not its first atomic task or implementation steps.>

Definition of Done
- <Binary, externally observable artifact or state.>
- <Required acceptance evidence tied to the exact resulting revision or environment.>
- <Evidence that the complete stage, rather than only its first constituent task, reached its terminal condition.>

Current State / Baseline
- <Repository/project, branch, exact SHA, working-tree state, and destination reachability with provenance labels.>
- <Recently completed outcomes and currently open issue/PR/blocker relationships with provenance labels.>

Evidence Provenance
- [Verified YYYY-MM-DD HH:MM TZ] <Fact verified this turn and how.>
- [Existing evidence, not reverified this turn] <Qualified historical evidence.>
- [Inference] <Conclusion derived from named evidence.>
- [Unknown] <Relevant unresolved fact and its impact.>

Key Evidence / Locations
- <Issue, PR, CI run, spec, ADR, repository-relative path plus ref, exact SHA, command, or external artifact> -- <why it matters.>

Must-Preserve Decisions / Invariants
- <Controlling architecture or domain decision, invariant, project rule, and reason.>

Scope / Non-goals
- In scope: <the bounded outcome.>
- Out of scope: <work deliberately excluded from this phase.>

Authorization Boundary
- Allowed transitions: <read-only investigation and explicitly authorized implementation/testing/state changes.>
- Requires fresh user confirmation: <remote writes, production changes, spending, credential-dependent actions, external communication, destructive or irreversible actions, and unresolved product decisions unless already specifically authorized.>
- Forbidden transitions: <secret disclosure, authority expansion, unrelated changes, bypassing safeguards, or any action explicitly prohibited by the user/project.>

Dependencies / Ordering Constraints
- <Only verified causal prerequisites and required state reachability; do not prescribe an implementation checklist.>

Decision Policy
- Investigate questions answerable from the repository, tests, logs, project instructions, or live tracker state before asking the user.
- Ask only about unresolved product semantics, authorization, irreversible/high-risk choices, or critical conflicts that evidence cannot resolve.
- When current verified state conflicts with historical context, use the current state and report the conflict.
- Preserve unrelated changes and choose the narrowest safe action consistent with the target state.

Verification Strategy
- <Risk-proportional evidence chain, choosing as applicable from targeted tests, integration/E2E, build/typecheck/lint, runtime checks, and remote CI on the exact revision.>
- Historical green results are context, not current acceptance evidence.

Stop Conditions
- Stop before production writes, secret access or disclosure, spending, destructive/irreversible operations, unauthorized remote mutations, multiple unresolved product meanings, inaccessible required state, or critical factual conflicts.
- When stopped, report the exact blocker, evidence gathered, and smallest user decision or state change needed.

Freshness Rules
- Reverify working tree, branch/SHA, issue/PR, CI, deployment, and other mutable external state immediately before action that depends on it.
- Use ADR/CONTEXT/spec decisions as durable evidence only when not superseded.
- Tie acceptance evidence to the actual resulting revision/environment; never substitute historical test results.
- Do not read or echo secrets.

Final Reporting Contract
- Report changes, acceptance evidence, remaining uncertainty, authorization-gated items, and the next safe action.
- Distinguish local validation from remote CI and distinguish fact from inference.

Execution Requirements
1. Activate Goal mode through `create_goal` before every other action; confirm activation and keep the stage objective active until complete or genuinely blocked.
2. Read applicable project instructions and verify dynamic prerequisites before acting.
3. Resolve repository-relative paths in the destination checkout; treat source-checkout absolute paths only as labeled context.
4. Derive and execute constituent tasks as needed without reducing the stage goal to the first task.
5. Pursue the target state autonomously only within the stated Authorization Boundary.
6. Adapt implementation choices to evidence while preserving invariants, scope, and causal ordering.
7. Use `update_goal` only to mark the goal complete when the full Definition of Done is satisfied, or blocked when the runtime's genuine-blocker threshold is met.
8. Stop when the Definition of Done is met or a Stop Condition is reached; do not broaden the goal.
```

Point to authoritative artifacts instead of copying large content. Include a minimal excerpt only when the destination cannot access a required source. Redact credentials, authentication material, private tokens, and unnecessary personal data.

Before dispatch, check that the contract:

- names one target state and binary completion evidence;
- describes a stage that may contain multiple development tasks rather than one atomic task;
- contains all five elements: Goal, State, Constraints, Authority, and Evidence;
- is executable without access to the source conversation;
- distinguishes verified, historical, inferred, and unknown claims;
- makes allowed, confirmation-gated, forbidden, and terminal transitions explicit;
- contains causal dependencies rather than a construction recipe;
- preserves all applicable instructions and unrelated work.

## 5. Create one Goal-mode thread

Inspect the current host's thread and Goal tool schemas before dispatch. Do not rely on another Skill for this workflow.

1. Confirm that the destination runtime supports `create_goal`. If it does not, return the completed Goal Contract and create no thread because the required mode cannot be guaranteed.
2. For repository work, call `list_projects` and match the saved project rather than guessing. Use a project worktree for Git and project local for non-Git unless the user explicitly requests the saved project directly. Do not use a cloud destination unless its runtime is verified to support Goal mode.
3. Prove source-state reachability. Identify the required branch, HEAD, and working-tree changes and compare them with the destination base. Use `startingState` only when the user explicitly requests that exact state. If required state is otherwise unreachable, ask one minimal question and create no thread.
4. Call `create_thread` exactly once with the complete Goal Contract as its initial prompt and a concise stage-derived title. Omit model and reasoning overrides unless the user requested them. Do not use `fork_thread`.
5. Handle creation state without duplication:
   - For a ready `threadId`, call one bounded `wait_threads` observation using `hostId` when available. Inspect enough destination output to confirm that `create_goal` succeeded before treating the handoff as Goal-active.
   - For a queued `clientThreadId`, report setup as queued and Goal activation as pending. Never pass it to thread-only tools and never create a replacement thread.
   - A timeout, missing progress, or ambiguous response is not proof that creation failed. Inspect existing thread state before any retry; retry only after definitive no-creation caused by a corrected recoverable input error.
   - If the thread starts but `create_goal` fails or is not confirmed, report the created thread with Goal activation failed or unconfirmed. Do not send implementation instructions that bypass Goal mode and do not create another thread.
6. The destination must perform no investigation, planning, or implementation before its successful `create_goal` call. Goal activation is part of handoff acceptance, not an optional first implementation step.

Invocation of this Skill with an explicit request to hand off or start the next stage authorizes one thread creation and one Goal activation inside it after the stage and destination checks pass. It does not authorize execution of the stage in the source thread or any additional external mutation.

## 6. Report and stop

Return:

1. the selected next development stage, why it outranks alternatives, and why it is stage-level rather than an atomic task;
2. the exact Goal Contract sent, or the prepared contract when dispatch did not occur;
3. the destination identifier, thread startup state, and separately observed Goal activation state, or the exact no-dispatch reason;
4. the host's created-task directive when required.

After one dispatch attempt, stop. Leave stage execution to the Goal-mode destination thread.
