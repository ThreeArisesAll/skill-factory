---
name: refine-prompts
description: "Analyze and refine short, rough, vague, or underspecified prompts without inventing facts. Support two primary modes: (1) return exactly one copy-ready optimized prompt without analysis or execution when the user says “只优化提示词”, “优化但不执行”, “只返回提示词”, or otherwise requests a prompt-only rewrite; and (2) deeply analyze the likely underlying need, missing high-impact information, assumptions, constraints, output format, and acceptance criteria before producing a structured prompt when the user asks for requirement discovery or deeper optimization. Use when the user wants to clarify, rewrite, expand, structure, improve, or uncover the real goal behind a prompt for later AI use."
---

# Prompt Refinement and Requirement Analysis

Turn a rough request into a reliable, reusable prompt. Select the response mode before doing any work, preserve the user's intent, expose uncertainty when appropriate, and never present inferred requirements as known facts.

## Choose the response mode

Apply explicit user instructions before defaults.

### Prompt-only mode

Use this mode when the user asks to only optimize, rewrite, expand, clarify, or structure the prompt; says not to execute the underlying task; or requests only the final prompt.

- Refine only. Do not execute, research, implement, create files, call tools, or send the underlying request.
- Return exactly one copy-ready prompt in a `text` code block.
- Do not add analysis, explanations, headings, questions, alternatives, commentary, or a plan outside the code block.
- Preserve stated facts, language, names, constraints, and priorities.
- Use short labeled placeholders for material missing information instead of asking questions or inventing details.
- Improve an already precise prompt lightly rather than expanding it unnecessarily.

Treat an explicit “only,” “do not execute,” or equivalent restriction as the highest-priority mode instruction.

### Deep-analysis mode

Use this mode when the user asks to uncover the real need, deeply analyze intent, identify gaps, make assumptions visible, or explain how the prompt should be improved.

- Return a concise need interpretation, one optimized structured prompt, and only high-value follow-up questions.
- Refine the underlying request without performing it unless the user explicitly asks for both refinement and execution.
- Treat the “real need” as a reasoned hypothesis, never as hidden knowledge about the user.

### Refine-and-execute mode

Use this mode only when the user explicitly asks to optimize the prompt and then perform the optimized task.

- Produce the optimized prompt first.
- Execute it afterward under the normal rules, tools, safety constraints, and requested output format for the underlying task.
- Do not enter this mode when the user also says “only optimize” or “do not execute.”

If no mode is explicit, use prompt-only mode for a straightforward rewrite request. Use deep-analysis mode when the request is so brief or ambiguous that explaining assumptions materially improves its usefulness.

## Establish the task boundary

- Treat the supplied text as the prompt to refine unless the user clearly identifies another target.
- Match the user's language unless they request another language.
- Preserve fixed facts, terminology, constraints, priorities, and preferences from the conversation.
- Do not turn a prompt-refinement request into the underlying task by accident.

## Analyze the request

Use these dimensions internally in every mode. Expose them only in deep-analysis mode:

1. **Explicit request**: Identify what the user literally asked for.
2. **Underlying outcome**: Infer what decision, action, or result the output is meant to enable.
3. **Deliverable**: Determine the concrete artifact to produce.
4. **Audience and scenario**: Identify who will use the result, where, and for what purpose.
5. **Inputs and evidence**: Identify supplied materials, required sources, and missing dependencies.
6. **Constraints and priorities**: Separate hard constraints from preferences and resolve conflicts by stated priority.
7. **Quality bar**: Translate vague words such as “professional,” “detailed,” or “creative” into observable acceptance criteria.
8. **Uncertainty**: Separate known facts, strong inferences, tentative assumptions, and unanswered questions.

Include only dimensions that materially affect the prompt. Do not pad the result with generic observations.

## Handle missing information

In prompt-only mode, never ask follow-up questions. Insert concise placeholders such as `【目标受众】`, `【预算范围】`, or `【输出长度】` where answers would materially affect execution.

In deep-analysis mode, rank missing information by impact:

- **Blocking**: Ask the minimum necessary question before finalizing when different answers would change the task category, create material risk, or make a useful prompt impossible.
- **High leverage but non-blocking**: Produce a useful first-pass prompt, mark the assumption or placeholder, and list up to three concise follow-up questions.
- **Low impact**: Choose a sensible default and state it only if it matters.

Do not turn refinement into a long interview.

## Construct the optimized prompt

Include only sections that improve execution. Use this order when applicable:

1. Task and intended outcome
2. Role or perspective
3. Background, audience, and scenario
4. Inputs
5. Required deliverables
6. Method or decision rules
7. Hard constraints, prohibitions, preferences, and priorities
8. Output format
9. Acceptance criteria
10. Uncertainty and exception handling

Apply these rules:

- Lead with the concrete task and outcome; add a role only when expertise or perspective materially changes the result.
- Replace subjective adjectives with testable requirements.
- Separate “must,” “must not,” and “prefer.”
- State precedence when constraints may conflict.
- Request concise rationale, assumptions, evidence, risks, or verification steps when useful; never request hidden chain-of-thought.
- Require current sources and citations when the task depends on changing external facts.
- Use placeholders rather than fabricated names, numbers, budgets, dates, sources, or capabilities.
- Remove redundant instructions and ornamental role-play.
- Make the prompt self-contained enough to reuse outside the current conversation.

## Return the result

For prompt-only mode, return only:

```text
【可直接复制使用的完整提示词】
```

For deep-analysis mode, use:

### 需求解读

- **表层请求**: …
- **推测的核心目标**: …
- **关键交付物**: …
- **关键约束与成功标准**: …
- **假设与缺失信息**: …

### 优化后的结构化提示词

```text
【可直接复制使用的完整提示词】
```

### 可选补充问题

Include the optional question section only for blocking or high-leverage unknowns. Ask no more than three questions and briefly state what each answer would change.

Compress simple requests and omit empty fields. Follow the user's requested output format when it conflicts with the default structure.

## Self-check

Before responding, verify that:

- The selected mode matches the user's explicit instructions.
- Prompt-only mode contains one `text` code block and nothing else.
- The result preserves the user's facts and intended outcome.
- Inferences are labeled and missing facts are not invented.
- Constraints, priorities, format, and acceptance criteria are observable.
- The prompt is no longer than its complexity justifies.
