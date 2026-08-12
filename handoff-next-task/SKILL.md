---
name: handoff-next-task
description: "Create or explicitly fork exactly one new Codex task from the current task: select one concrete non-review objective, verify the required source state, compress evidence, decisions, and approval gates into a redacted self-contained prompt, dispatch it, and confirm startup. Use only when the user explicitly requests a new Codex task/thread/chat or a fork, or invokes $handoff-next-task; a document-only handoff is outside this skill."
---

# Handoff Next Task

Transfer operational state into exactly one new Codex task. Produce a launchable prompt, not a transcript summary.

## 1. Fix the boundary

- Treat the current task as the source and one new peer task, created normally or explicitly forked, as the destination.
- Treat text passed with `$handoff-next-task` as the requested focus. Otherwise derive the narrowest unfinished objective supported by the conversation and label it as inferred.
- Define one objective with an intended artifact or state change and observable completion evidence.
- Treat code review as an ineligible next objective. This includes initial review, re-review, auditing changes, reviewing another agent's implementation, and open-ended searches for more issues, whether supplied explicitly or inferred. Never create a review task from this skill.
- Convert review evidence into forward work: implement a specific validated fix, add targeted regression coverage, complete acceptance validation, or surface a concrete human decision. A bounded verification step may support the outcome but cannot be the task's primary objective.
- When the supplied focus is review-only, ask for one eligible non-review objective before creation. When no authorized forward action exists, report that there is no eligible next task.
- Ask one concise blocking question before creation when materially different objectives remain or the destination choice would determine whether required state is accessible.
- Carry forward existing authorization only. Creating the new task does not authorize publishing, spending, credential use, destructive operations, repository or tracker writes, external communication, or unresolved product decisions.

Complete this step when exactly one non-review objective, its done condition, and every surviving approval gate are explicit.

## 2. Refresh the evidence

Review the conversation and directly relevant task-local artifacts. Use lightweight read-only checks to refresh mutable facts that the next task would otherwise trust, for example:

- repository root, saved project, current branch and HEAD commit, worktree status, relevant diff scope, and the intended destination base;
- whether the objective depends on commits or working-tree changes absent from that destination base;
- existence and current location of referenced files or generated artifacts;
- current issue, pull request, deployment, or external-object status when it controls the next action;
- the most recent relevant validation command and result.

Use existing evidence instead of performing substantial new work solely for the handoff. Label claims so the destination can judge freshness:

- `[Verified <date/timezone>]` or the user's-language equivalent for facts checked in this turn;
- `[Existing evidence, not reverified this turn]` for earlier test results or observations;
- `[Inference]` for the selected objective or other reasoned conclusions;
- `[Unknown]` for unresolved or inaccessible facts.

Complete this step when every mutable claim needed for the next action is either freshly verified or explicitly marked as stale, inferred, or unknown, and every required source-state dependency is known to be reachable or called out as inaccessible.

## 3. Compress the handoff

Include only state that changes what the destination should do:

- the original outcome and the single next objective;
- completed work, current state, and validation evidence;
- decisions with reasons that must remain in force;
- user instructions, project rules, scope exclusions, and approval gates;
- unresolved questions, blockers, failed attempts, risks, and invalidation signals;
- repository-relative paths with the relevant commit or branch, absolute paths for repository-external artifacts, commands, URLs, and external identifiers;
- suggested installed skills, named exactly, with a one-line reason to invoke each. Exclude `code-review` and other review-only skills; prefer skills that implement, fix, test, or produce the selected outcome.

Point to existing specs, plans, ADRs, issues, commits, diffs, and logs instead of copying them. State why each pointer matters. Resolve repository-relative paths against the destination checkout, and label source-checkout absolute paths as context rather than edit targets. If the destination cannot access a required source, include only the minimum excerpt needed to act.

Remove secrets, credentials, tokens, authentication material, and unnecessary personal data. Refer to the secure source or the retrieval step, never the value. Exclude hidden reasoning and unsupported claims.

Keep the handoff in the new task prompt. If the user also requests a handoff file, write the same redacted content to the operating system's temporary directory rather than the repository or workspace.

Complete this step when the handoff is self-contained for action, pointer-rich instead of duplicative, and safe to transmit.

## 4. Assemble the launch prompt

Match the user's language. Preserve exact technical names, paths, commands, identifiers, and error text when translation would reduce precision. Use this structure and omit empty sections:

```text
Task: <one concrete next objective>

Definition of done:
- <observable artifact or state>
- <required validation evidence>

Background and current state:
- <original intended outcome>
- <completed work and current state, each with evidence labels>
- <required source branch, commit, or working-tree state and its destination reachability>

Key evidence and locations:
- <repository-relative path plus commit/ref, external absolute path, URL, command, or external ID> — <why it matters>

Must-preserve decisions and boundaries:
- <decision and reason>
- <scope, exclusion, project rule, or human approval gate>

Open items and risks:
- <unknown, blocker, failed attempt, risk, or invalidation signal>

Suggested skills:
- $<exact-installed-skill-name> — <when and why>

Execution requirements:
1. Read the applicable project instructions first, then inspect the live state relevant to this objective.
2. Resolve repository-relative paths against this task's checkout; use source-checkout absolute paths only as labeled context.
3. Continue from the listed artifacts and evidence; repeat completed work only when its evidence is stale or invalid.
4. Preserve unrelated user changes and parallel edits.
5. Proceed autonomously within the existing authorization; leave unresolved human decisions to the user.
6. Make delivery, implementation, repair, or acceptance the primary objective; do not expand code review, re-review, or continued issue hunting into a follow-up task.
7. Validate in proportion to risk, then report changes, evidence, remaining uncertainty, and the next safe action.
```

Complete this step when the prompt has exactly one actionable non-review objective, testable completion criteria, sufficient evidence to start, no transcript dump, and no sensitive value.

## 5. Dispatch and observe one task

Use the current host's task-management tools and inspect their live schemas when necessary. In the Codex desktop app:

1. Use `list_projects` before creating repository-backed work. Match the actual saved project instead of guessing.
2. Prove source-state reachability before dispatch:
   - identify the branch, HEAD commit, and working-tree changes required by the objective;
   - determine whether the intended destination starts from a base that contains that state;
   - when the default destination base omits required commits or working-tree changes, ask one blocking question that names the accessible branch, working-tree state, or alternate destination the user can authorize;
   - pass `create_thread` a `startingState` only after the user explicitly requests the current working tree or a particular existing branch. Do not dispatch into a destination that lacks required state.
3. Select the destination from evidence:
   - use a project task for repository or saved-project work;
   - default to a worktree for Git projects and to the saved project's local environment for non-Git projects;
   - use a projectless task for work without a repository;
   - use ChatGPT Work cloud only when the user explicitly requests it;
   - for a fork, use only an environment whose state reachability is proven. Follow an explicitly requested environment; when none is requested, preserve the current directory.
4. Dispatch exactly one task after the prompt and destination checks pass:
   - for a new task, call `create_thread` with the complete prompt and a concise objective-derived title;
   - for an explicit fork, call `fork_thread`; when it returns `threadId`, immediately send the complete launch prompt with `send_message_to_thread` because a fork copies completed history but does not start the new objective;
   - omit model and reasoning overrides unless the user requested them.
5. Handle the returned state exactly:
   - when a ready `threadId` has received its launch prompt, pass it with `hostId` when available to one bounded `wait_threads` call and report the latest observed progress or attention state;
   - when only `clientThreadId` is returned, report worktree setup as queued and do not pass that identifier to thread-only tools. For a queued fork, state that the launch prompt is prepared but not yet sent and return it as the recoverable result;
   - when prompt delivery fails, or when waiting or observation fails or returns no progress, report the task as created or forked but startup unconfirmed; preserve the result and do not recreate it;
   - when dispatch fails or the result is ambiguous, inspect existing task state before any retry. Retry only after a definitive no-dispatch result and a corrected recoverable input error. Never create a second task merely because dispatch or waiting is delayed.

Explicit invocation or an explicit request for a new task or fork is authorization for one dispatch; no duplicate confirmation is needed after the prompt and destination pass the checks above.

Complete this step when one task is ready with its prompt delivered and observed, queued with its client identifier and delivery state explicit, or accurately reported as not dispatched with the tool limitation or error preserved.

## 6. Report and stop

Return:

1. the concise handoff summary and selected objective;
2. the exact prompt sent to the destination, or the prepared-but-unsent prompt for a queued fork;
3. the task identifier and observed status, or the exact reason no task was dispatched;
4. the host directive on its own line after successful dispatch:
   - `::created-thread{threadId="..."}` for a ready task;
   - `::created-thread{clientThreadId="..."}` for queued worktree setup.

If no eligible non-review objective exists, state that no task was dispatched and identify the concrete input or authorization required to form one. If task tools are unavailable, return the finished prompt as the recoverable result and state that dispatch did not occur. After confirmed startup, leave execution of the next objective to the destination task.

Complete the handoff only when the user can identify the destination, distinguish created, forked, queued, and failed states, and tell whether the launch prompt was delivered.
