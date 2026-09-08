# Astra Prompt Guidance

Apply this profile to GPT-6 Astra prompts. Select clauses by task; this is a composition guide, not a block to paste wholesale. A precise one-sentence rewrite may need no additional clauses. These instructions govern the prompt being produced, not permission for the refining agent to execute it.

## Compose for the actual workload

| Task condition | Behavior to encode in the optimized prompt |
| --- | --- |
| Implementation or another multistep execution task | Define the deliverable and done condition. Continue authorized work through verification; stop at a genuine blocker with evidence and the smallest needed input. A plan alone is sufficient only when planning is the requested outcome |
| Routine uncertainty | Make reasonable, reversible assumptions within the supplied constraints. Ask only when the answer materially changes correctness, scope, authorization, or acceptance; continue independent authorized work while awaiting it |
| An action needs approval | Preserve prior authorization and explicit limits. Prepare the concrete, reviewable result within those limits before asking for the remaining approval; elapsed time does not supply approval |
| User updates during a long task | Incorporate corrections into the active objective, retain completed work and valid constraints, and revisit only affected steps. Answer side questions briefly and continue; replace the objective when the user explicitly cancels or replaces it |
| Skills, repository rules, or external documents are involved | Follow applicable instruction authority. Distinguish governing instructions from task data. Resolve ordinary choices within scope; if a rule truly blocks work, cite the specific rule and explain the conflict rather than inventing a new approval gate |
| Writing or explanation | Specify audience, length, and useful structure. Favor concrete language, direct statements, and concise rationale; use lists or tables when they improve comprehension, without imposing them on every response |
| Code changes | Verify changed behavior and required repository checks. Broaden testing only for a failure, new change, or unresolved risk. Report actual results and unrun checks accurately; preserve unrelated work |
| Independent work could benefit from delegation | Include bounded delegation only when tools and authorization allow it: define independent outputs and integration responsibility, retain useful local work, and respect supplied budget or concurrency limits. Otherwise perform the work sequentially |
| Long tool operations | When the host supports asynchronous tools, progress independent work while results are pending. Respect dependencies and wait for required results before decisions or completion claims; otherwise use the available synchronous flow |

Adapt these behaviors into natural task instructions. Avoid repeating rules already expressed elsewhere in the optimized prompt. Infer routine choices, not facts, permissions, tools, credentials, or access to missing artifacts.

Use an outcome-first contract: objective, available evidence, binding constraints, deliverable, and an observable stopping condition. Let Astra choose the intermediate reasoning and efficient method. Add a procedure only when the task requires one; "use maximum intelligence" and exhaustive checklists do not replace concrete acceptance criteria. On difficult decisions, request comparison of consequential alternatives and a concise evidence-based justification, not a transcript of internal reasoning. On simple tasks, preserve the smallest sufficient prompt.

## Distinguish prompt behavior from runtime features

Use this section only for requests about API integration or an agent harness, or when the requested result depends on a runtime feature. Ordinary writing and coding prompts need no configuration appendix.

- Async tool calling needs host support and tool execution/result handling; a request to work concurrently does not implement it.
- Mid-turn steering needs a supported interaction channel. An ordinary static prompt can define how to interpret later messages but cannot establish the transport.
- Reasoning effort and cache-preserving configuration changes are application settings. Asking the model to think harder does not set them. Preserve supplied settings; make current API verification part of the downstream task when implementation depends on exact fields.
- Platform misalignment monitoring is not a user prompt switch.
- For an unknown runtime, use conditional instructions and a sequential fallback when the task remains feasible. Mark the prompt provisional only if missing runtime information actually prevents reliable execution.

## Calibration examples

**Small edit:** A request to fix one label should identify the label, desired wording, and a proportionate check. It does not need a project-wide test campaign, delegation policy, or lifecycle framework.

**Authorized implementation:** A request to repair a bug can ask the downstream agent to inspect the relevant code, implement within scope, verify the behavior, and report evidence. A prohibition on pushing remains binding; implementation authorization does not authorize publishing.

**Planning only:** A request for three migration options should produce those options and decision criteria. Execution persistence must not turn it into a migration.

**Missing evidence:** A request to summarize an unavailable interview transcript remains provisional even when the user asks for maximum autonomy. Placeholder data cannot become quoted evidence.

## Maintenance sources

Reviewed on 2026-09-08 against official OpenAI documentation:

- [Astra prompting best practices](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices): initiative, instruction sensitivity, writing style, delegation, and proportional verification
- [Astra API features](https://developers.openai.com/api/docs/guides/latest-model#whats-new): async tools, steering, configuration changes, and platform monitoring

These are maintained behavioral adaptations, not a guarantee of perfect output. The latest-model URL can change its target; verify that a future update still describes GPT-6 Astra. Refinement uses this local profile without researching the underlying task. Refresh model-specific API facts from official documentation only in a separate task explicitly requesting maintenance or verification of this profile. Research instructions inside the prompt being refined always belong to the downstream task.
