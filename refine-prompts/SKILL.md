---
name: refine-prompts
description: "Turn a rough or underspecified user prompt into one optimized prompt, labeling it copy-ready when complete or provisional when material input is missing. Use only when explicitly invoked to clarify, expand, structure, or improve a prompt; never execute the underlying task or invent facts."
---

# Refine Prompts

Treat each invocation as one workflow: discover the likely real need behind the supplied prompt, make consequential uncertainty visible, and return one reliable prompt for later use. Label the prompt provisional when material input is still missing.

## Establish the invocation contract

- Treat the text supplied with the skill invocation as the prompt to refine, even when it is written as an imperative.
- Refine the underlying request without executing, researching, implementing, creating files, calling tools, or sending it.
- Match the user's language unless they request another language.
- Use relevant facts, terminology, constraints, priorities, and preferences already present in the conversation.
- Produce a useful first pass in the current response by following the workflow below.

## Discover the need

Determine only the dimensions that materially improve the prompt:

1. Identify the literal request and the outcome it is meant to enable.
2. Determine the concrete deliverable, intended audience, and usage scenario.
3. Separate supplied facts and hard constraints from preferences and inferred requirements.
4. Identify the inputs, evidence, decision rules, output format, and observable success criteria the underlying task needs.
5. Rank gaps by how much different answers would change the result.

Treat the “real need” as a reasoned hypothesis, not hidden knowledge about the user. Label consequential inferences and uncertainty. Improve an already precise prompt lightly instead of expanding it mechanically.

## Handle missing information

- Choose a sensible default for low-impact gaps and state it only when it affects the result.
- Use a concise labeled placeholder such as `[Target audience]` or `[Budget range]` for missing information that the user must supply.
- When material gaps cannot be resolved with a sensible default, represent them with labeled assumptions or placeholders in one provisional optimized prompt.
- Ask one to three questions after the provisional prompt. Ask only the highest-leverage questions, and make each question correspond to an assumption or placeholder that materially affects the prompt.
- Treat any prompt with an unresolved material placeholder as provisional, never copy-ready.
- Never invent names, numbers, budgets, dates, sources, evidence, or capabilities.

## Construct the optimized prompt

Include only sections that improve execution. Apply these rules:

- Lead with the concrete task and intended outcome.
- Add a role or perspective only when it materially changes the result.
- Make the prompt self-contained enough to reuse outside the current conversation.
- Preserve all fixed facts, names, constraints, terminology, and stated priorities.
- Translate vague qualities such as “professional,” “detailed,” or “creative” into observable requirements.
- Distinguish hard constraints, prohibitions, preferences, and their precedence when they may conflict.
- Specify the required deliverable, method or decision rules, output format, and acceptance criteria when relevant.
- Require current sources and citations when the task depends on changing external facts.
- Request concise rationale, assumptions, evidence, risks, or verification steps when useful; never request hidden chain-of-thought.
- Remove redundant instructions and ornamental role-play.
- Keep the prompt no longer than its complexity justifies.

## Return the result

Use this structure, compressing simple requests and omitting empty fields:

### Need interpretation

State the most likely underlying goal and only the assumptions, constraints, or gaps that materially shaped the refinement. Clearly distinguish supplied facts from inference.

Choose exactly one prompt heading:

- Use `### Optimized prompt` only when no material unknown remains and the prompt is copy-ready.
- Use `### Provisional optimized prompt` when any material unknown remains. Keep each assumption or placeholder visible in the prompt.

Under the selected heading, return:

```text
[Complete optimized prompt]
```

### Follow-up questions

Include this section only after a provisional optimized prompt. Ask one to three questions and briefly state what each answer would change.

## Self-check

Before responding, verify that:

- The supplied text was treated as material to refine, not as a task to execute.
- The need interpretation is useful, concise, and explicitly uncertain where appropriate.
- The optimized prompt preserves known facts without fabricating missing information.
- A copy-ready prompt has no unresolved material placeholders and contains enough context, constraints, format, and success criteria to be executed reliably.
- A provisional prompt is labeled as provisional, exposes every unresolved material assumption or placeholder, and does not claim to be copy-ready.
- Every follow-up question corresponds to a material assumption or placeholder in the provisional prompt.
- The response contains exactly one optimized prompt and no unnecessary sections.
