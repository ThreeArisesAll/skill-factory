# Need Discovery

Use this branch when the entrypoint identifies consequential uncertainty about the problem or direction. Its purpose is to refine the user's request, not diagnose their life, perform research, or execute the underlying task.

## Establish the problem and decision

Privately map the relevant relationships, using supplied context:

- Situation: Who is affected, in what setting, and why does this matter now?
- Obstacle: What observed difficulty or unmet need prompted the request?
- Desired change: What should become possible or improve?
- Proposed means: Which artifact or action has the user requested, and how is it expected to help?
- Evidence of success: What would demonstrate a useful result, beyond merely producing the artifact?

Use only dimensions that could change the prompt. Unknown motivations, metrics, and constraints stay unknown. An operational need is enough; do not invent emotional or psychological motives.

Classify consequential statements as supplied facts, context-supported inferences, or hypotheses requiring validation. Preserve reported observations while keeping the user's explanation of their cause distinguishable from established evidence.

## Recover intent from sparse language

Use a short evidence ladder rather than a long interview:

1. Resolve what "this," "better," or "help" refers to using the nearest relevant supplied context. A supplied artifact and audience can already determine the task.
2. Connect the requested means to the practical change the user wants. For "get my evenings back; I keep working late," the supported outcome is protecting non-work time; the cause of overtime is still unknown. Do not assume poor discipline, a demanding manager, or a particular profession.
3. Identify the uncertainty that would most change the next action. Distinguish a missing prerequisite from evidence the requested investigation is meant to gather. Apply the entrypoint's [readiness rule](../SKILL.md#readiness-rule) to the next deliverable; preserve the user's requested stage.
4. Test a competing interpretation only when a concrete clue supports it. If one interpretation is well supported and reversible, use it with a brief assumption. If materially different directions remain, keep the choice visible. If there are no clues at all, ask for the object and desired change; do not invent candidate industries or personal motives.

For consequential inferred requirements, retain a concise connection between clue, interpretation, and effect on the prompt. Confidence is qualitative and evidence-based; do not invent probabilities. Infer acceptance criteria from the task's purpose, but mark any proposed metric as a proposal and preserve unknown baselines.

When questions are prohibited, make the prompt useful through explicit assumptions, conditional branches, or an in-scope diagnostic step. A downstream diagnostic step must also honor the no-questions constraint: use available evidence, state what cannot be determined, and avoid smuggling an interview into the generated prompt. If no object or direction can be recovered, a minimal provisional input contract is the honest result.

## Check the direction without replacing it

- Preserve explicit commitments: a chosen technology, output, scope, or instruction to skip strategy remains binding. Refine within it even when another route seems attractive.
- Treat explicit tentative wording such as "maybe" or "I think" as a proposal without asking the user to reconfirm that status. Ask about the evidence or obstacle that would change the choice, not whether an already tentative idea is final. Treat tentative means as proposals. When there is a concrete gap between the proposed means and the desired outcome, describe that gap briefly. Suggest a reframing, but do not silently substitute a different deliverable.
- When two or three plausible interpretations would require different work, identify only those supported by the context. State the clue for each and what choice would change. Do not generate alternative theories merely to fill a quota.
- For conflicting constraints, first check whether a straightforward interpretation satisfies both. If a real conflict remains, preserve both in a provisional prompt. Ask which takes precedence only when questions are permitted; otherwise state the unresolved priority and limit work to what does not require choosing a branch.
- Separate artifact acceptance from outcome evidence when they differ. A completed landing-page redesign does not establish improved registration. Preserve supplied metrics; propose an evaluation method without inventing targets, baselines, or promised effects. When the stated outcome and requested proxy can both be measured within scope, preserve the requested work and evaluate both without inventing a priority approval gate. Mark newly recommended metric roles as proposals rather than user decisions. Ask only when a real decision cannot satisfy both or a binding requirement must change.

## Ask to discriminate, then update

Choose the smallest question that separates the leading interpretations or resolves the most consequential conflict. Prefer an observable example, workflow step, or intended decision to an abstract request for the user's "real goal". Explain what its answer changes and use the entrypoint's one-to-three-question limit.

For example, when a support diagnosis or intervention decision requires workload evidence and questions are permitted, ask which work consumes the most effort: repeated questions, finding information for difficult cases, or handling peaks. A diagnostic-plan prompt can instead identify that evidence for later inspection. These are possible explanations, not findings; the bot's tone does not resolve the direction.

If the user has already supplied the discriminating evidence, use it. If they cannot answer, encode the uncertainty and a bounded validation step only when that fits the requested deliverable. If they forbid questions, keep that constraint inside the prompt and state limitations without requesting information. In both cases, use the entrypoint's readiness rule; the presence of uncertainty or a no-questions instruction does not determine the label by itself.

After an answer, update the interpretation and the single prompt. Keep confirmed goals and constraints, remove disproven hypotheses, and ask again only if a different material gap remains. Stop discovery once the direction is sufficiently determined; do not keep asking why.

## Carry the discovery into one usable prompt

Include the supported objective, requested deliverable, decision-relevant context, constraints, and completion criteria. Where a reframing awaits agreement, preserve the original request and make the alternative conditional; avoid producing several competing optimized prompts.

Use the need interpretation for a brief explanation of consequential inferences. The optimized prompt must retain enough of those assumptions and unresolved choices to be safe to copy independently. Questions should correspond to visible gaps in that prompt.

## Calibration

- "Make the homepage prettier because users are not registering": preserve the visual request, distinguish appearance from the unverified registration hypothesis, and ask for the observed drop-off or evidence only if it determines the direction.
- "We have decided on a chatbot; refine the implementation brief without revisiting that choice": respect the decision and clarify only what implementation needs.
- "Compare competitors so we can choose a pricing model": use the supplied decision to focus the comparison; do not ask what the report is for again.
- "Include every detail in a ten-second spoken summary": expose the feasibility conflict, clarify priority when questions are permitted, and otherwise state the unresolved constraint instead of promising both.
- "Change this exact label, preserving layout": use light refinement; no strategy questions, causal analysis, or success-metric invention.
