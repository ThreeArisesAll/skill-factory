---
name: handoff-next-task
description: "Create or explicitly fork exactly one new Codex task from the current task: select one concrete non-review delivery objective, verify required source state, compress evidence and approval gates into a redacted launch prompt, dispatch it, and confirm startup. Use only when the user explicitly requests a new Codex task/thread/chat or a fork, or invokes $handoff-next-task; a document-only handoff is outside this skill."
---

# Handoff Next Task

Transfer operational state into exactly one new Codex task. Produce a launchable prompt, not a transcript summary.

## 1. Fix the boundary

- Treat the current task as the source and one new peer task, created normally or explicitly forked, as the destination.
- Treat text passed with `$handoff-next-task` as the requested focus. Otherwise infer the narrowest unfinished objective supported by the conversation and label it `[Inference]`.
- Define one **delivery objective**: an authorized implementation, repair, regression test, acceptance outcome, or specific human decision with observable completion evidence.
- Treat review, re-review, audit, reviewing another agent, and open-ended issue hunting only as evidence. Convert validated findings into a delivery objective; when the supplied focus is review-only and no authorized forward action exists, ask for one eligible objective or report that none exists.
- Ask one concise blocking question only when materially different objectives remain or destination choice controls required-state access.
- Carry forward existing authorization only. Dispatch does not authorize publishing, spending, credential use, destructive operations, repository or tracker writes, external communication, or unresolved product decisions.

Complete this step when one delivery objective, its done condition, and every surviving approval gate are explicit.

## 2. Refresh the evidence

Review the conversation and directly relevant task-local artifacts. Refresh only mutable facts the destination must trust:

- repository root, saved project, branch, HEAD, worktree and diff state, intended destination base, and whether required changes are reachable there;
- referenced artifacts, controlling issue/PR/deployment/external-object status, and the latest relevant validation result.

Use existing evidence instead of performing substantial new work solely for the handoff. Label each destination-relevant claim with the user's-language equivalent of `[Verified <date/timezone>]`, `[Existing evidence, not reverified this turn]`, `[Inference]`, or `[Unknown]`.

Complete this step when every mutable claim is verified or qualified and every required source-state dependency is reachable or explicitly inaccessible.

## 3. Compress the handoff

Include only state that changes destination action:

- original outcome, delivery objective, completed work, current state, and validation evidence;
- decisions and reasons, user instructions, project rules, exclusions, and approval gates;
- open questions, blockers, failed attempts, risks, and invalidation signals;
- repository-relative paths with commit/ref, absolute paths for external artifacts, commands, URLs, and identifiers;
- installed implementation, repair, test, or production skills named exactly with a one-line reason. Exclude `code-review` and other review-only skills.

Point to existing specs, plans, ADRs, issues, commits, diffs, and logs instead of copying them, and state why each pointer matters. Resolve repository-relative paths in the destination checkout; label source-checkout absolute paths as context, not edit targets. Include a minimum excerpt only when a required source is inaccessible.

Redact secrets, credentials, authentication material, and unnecessary personal data. Refer to the secure source or retrieval step, never the value. Exclude hidden reasoning and unsupported claims.

Keep the primary handoff in the launch prompt. If the user also requests a file, use their explicit path; when they give no path, use the operating system's temporary directory. Do not choose a repository or workspace path by default.

Complete this step when the handoff is self-contained, pointer-rich, safe to transmit, and stored only where authorized.

## 4. Assemble the launch prompt

Match the user's language. Preserve exact technical names, paths, commands, identifiers, and error text when translation would reduce precision. Use this structure and omit empty sections:

```text
Task: <one delivery objective>

Definition of done:
- <observable artifact or state>
- <required validation evidence>

Background and current state:
- <original outcome, completed work, and current state with evidence labels>
- <required branch, commit, or working-tree state and its destination reachability>

Key evidence and locations:
- <repository-relative path plus commit/ref, external absolute path, URL, command, or identifier> — <why it matters>

Must-preserve decisions and boundaries:
- <decision and reason>
- <scope, exclusion, project rule, or approval gate>

Open items and risks:
- <unknown, blocker, failed attempt, risk, or invalidation signal>

Suggested skills:
- $<exact-installed-skill-name> — <when and why>

Execution requirements:
1. Read applicable project instructions, then inspect live state relevant to this objective.
2. Resolve repository-relative paths in this checkout; use source-checkout absolute paths only as labeled context.
3. Continue from valid evidence, preserve unrelated changes, and repeat work only when its evidence is stale or invalid.
4. Proceed within existing authorization and leave unresolved human decisions to the user.
5. Keep the delivery objective primary; use review evidence only to support implementation, repair, testing, acceptance, or a specific human decision.
6. Validate in proportion to risk, then report changes, evidence, uncertainty, and the next safe action.
```

Complete this step when the prompt has one delivery objective, testable completion criteria, sufficient evidence, no transcript dump, and no sensitive value.

## 5. Dispatch and observe one task

Inspect the current host's task-tool schemas before use. In the Codex desktop app:

1. Before `create_thread` for repository work, use `list_projects` and match the saved project instead of guessing.
2. Prove source-state reachability: identify required branch, HEAD, and working-tree changes; compare them with the destination base. If required state is absent, ask one question naming an accessible existing branch, working-tree state, or alternate destination. Pass `startingState` only after the user explicitly requests that state; never dispatch to an inaccessible base.
3. Select one destination:
   - for `create_thread`, use a project worktree for Git unless the user explicitly requests the saved project directly, project local for non-Git, projectless without a repository, and ChatGPT Work cloud only on explicit request;
   - for an explicit `fork_thread`, use a proven-accessible requested environment or preserve the current directory when none is requested.
4. Dispatch once:
   - call `create_thread` with the complete prompt and a concise objective-derived title; or
   - call `fork_thread`, then immediately send the complete prompt with `send_message_to_thread` when it returns `threadId`, because a fork copies completed history but does not start the objective;
   - omit model and reasoning overrides unless requested.
5. Handle the result:
   - after a ready `threadId` receives the prompt, pass it and `hostId` when available to one bounded `wait_threads` call;
   - for `clientThreadId`, report queued setup and never pass it to thread-only tools. For a queued fork, return the prepared-but-unsent prompt;
   - if prompt delivery fails or observation fails or yields no progress, report created/forked with startup unconfirmed and do not recreate;
   - after failed or ambiguous dispatch, inspect existing tasks before retrying. Retry only after definitive no-dispatch plus a corrected recoverable input error; delay alone never justifies a second task.

Explicit invocation or an explicit new-task/fork request authorizes one dispatch; no duplicate confirmation is needed after prompt and destination checks pass.

Complete this step when one task is ready, prompt-delivered, and observed; queued with delivery state explicit; or accurately reported as not dispatched.

## 6. Report and stop

Return:

1. the selected delivery objective and concise handoff summary;
2. the exact sent prompt, or the prepared-but-unsent prompt for a queued fork;
3. the identifier and observed status, or the exact no-dispatch reason;
4. after successful dispatch, the host directive on its own line:
   - `::created-thread{threadId="..."}` for a ready task;
   - `::created-thread{clientThreadId="..."}` for queued worktree setup.

If no delivery objective exists, identify the input or authorization needed and report no dispatch. If task tools are unavailable, return the finished prompt and state that dispatch did not occur. After confirmed startup, leave execution to the destination task.

Complete the handoff when the user can identify the destination, distinguish created, forked, queued, and failed states, and tell whether the prompt was delivered.
