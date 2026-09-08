# Baseline generated responses

## Case 2

### Need interpretation

You want a marketing plan for a new app. The app's purpose, intended users, business objective, and available resources are missing; those inputs determine which channels and activities are appropriate.

### Provisional optimized prompt

```text
Create a practical marketing plan for my new app that connects the marketing activities to the outcome below.

Context:
- App and core benefit: [What the app does and why someone would choose it]
- Intended users and market: [Target users, geography, and language]
- Launch stage and marketing objective: [Current stage and the result the plan should prioritize]
- Resources and planning horizon: [Budget, available people or time, and relevant dates]

Recommend positioning, key messages, acquisition channels, and a prioritized sequence of activities suited to this context. Explain briefly why each priority fits the audience and available resources. Include practical first steps, dependencies, and a way to measure whether each activity contributes to the objective.

Distinguish supplied facts from assumptions. Do not invent customer research, market statistics, budgets, or expected results. If recommendations depend on current external facts, verify those facts and cite the sources. Present a concise strategic overview followed by an actionable plan; identify the largest remaining uncertainties and inexpensive ways to test them.
```

### Follow-up questions

1. What does the app do, and who is it for? This determines positioning and audience selection.
2. What stage is the app at, and what result should marketing achieve first? This determines whether the plan prioritizes validation, launch, acquisition, or another outcome.
3. What resources and timeframe are available? This determines the feasible channels and sequence of work.

## Case 4

### Need interpretation

You want a narrowly scoped local checkout copy change, with verification that layout and behavior remain intact. Committing and pushing are explicitly excluded.

### Optimized prompt

```text
In the existing checkout UI, change the button label from “Buy” to “Place order”. Preserve its layout, styling, and behavior, and leave unrelated work intact.

Inspect the relevant component and applicable repository instructions, make the smallest local edit, and run a proportionate check of the updated label and unchanged layout and behavior. Report the file changed and the checks actually performed, including any verification limitation. Continue through the local edit and verification; if blocked, report the concrete blocker and the smallest input needed to proceed.

Do not commit or push.
```

## Case 11

### Need interpretation

You report that users are not registering and want a homepage redesign. The idea that visual appearance causes the registration problem is a hypothesis. The redesign should retain your visual objective while making that uncertainty explicit; the current homepage and any observed registration friction would determine the specific changes.

### Provisional optimized prompt

```text
Redesign our homepage to improve its visual quality and make the path to registration clear.

Context:
- Current homepage: [URL, screenshots, or source files]
- Product and intended visitors: [What we offer and who the homepage serves]
- Reported problem: Users are not registering
- Working hypothesis: Improving the homepage's appearance may help; this has not been established as the cause
- Available evidence: [Observed registration friction or funnel evidence, or “none available”]

Review the supplied homepage and context before choosing changes. Improve visual hierarchy, readability, spacing, consistency, and the clarity of the registration action while preserving accurate product claims and existing functionality.

Keep the redesign as the requested deliverable. If evidence suggests that the main obstacle lies elsewhere, explain the finding and propose any broader work separately for approval. Do not silently replace the redesign with another project or claim that visual polish will increase registrations.

Deliver the revised homepage and a concise explanation of the main design decisions. Check the result across relevant screen sizes and verify that the registration path still works. Distinguish completion of the redesign from evidence of improved registration; propose a practical way to evaluate the latter without inventing a baseline or promised uplift.
```

### Follow-up questions

1. Can you provide the current homepage and briefly identify its product and intended visitors? This determines what can be redesigned and what the page needs to communicate.
2. Where do visitors appear to stop before registering, if you have that evidence? This determines which homepage changes are justified and whether any separate investigation should be proposed.

## Case 14

### Need interpretation

You want a reusable template, so the report's later arrival is expected. The unresolved issue is the conflict between preserving every detail of a 100-page report and fitting a spoken summary into ten seconds; the template needs a priority rule before it can reliably satisfy the request.

### Provisional optimized prompt

```text
Summarize the report supplied with this template for spoken delivery.

Input contract:
- Report: [Provide the complete report when using this template]
- Constraint priority: [Choose “ten-second limit” or “exhaustive coverage”]

The original request calls for exhaustive coverage of every detail in a 100-page report and a spoken duration of no more than ten seconds. Do not claim that both can be guaranteed.

If the ten-second limit takes precedence, produce a highly selective spoken summary of the report's central finding or conclusion, using a conservative speaking-rate estimate and noting separately that details were omitted. Do not describe it as exhaustive.

If exhaustive coverage takes precedence, produce a spoken script that covers the report's substantive details, preserving qualifications and distinctions. State its estimated duration and make clear that the ten-second limit has been relaxed.

Base the script only on the supplied report. Do not invent findings or remove qualifications that would change its meaning. Return the script, a brief duration estimate with its basis, and the applicable coverage limitation. If the constraint priority is still unspecified, request that choice before drafting the script.
```

### Follow-up questions

1. Which takes precedence: the ten-second limit or exhaustive coverage? This determines whether the template produces a very selective summary or a substantially longer script.

## Case 18

### Need interpretation

The measured burden is searching internal policy documents for complex support cases. The direction is now settled: an internal policy-search assistant, with a plan as the deliverable and no customer-facing bot or implementation.

### Optimized prompt

```text
Develop a practical plan for an internal policy-search assistant that helps support staff find reliable answers in internal policy documents when handling complex cases.

Context:
- Support is overloaded
- We measured the work and found that most effort goes into searching internal policy documents for complex cases
- We have decided against a customer-facing bot
- The deliverable is a plan only; do not implement or change any systems

Focus the plan on the staff workflow: receiving a complex question, locating the relevant policy, checking its applicability and currency, and reviewing the evidence before responding to the customer. Keep support staff responsible for interpreting and using the result.

Cover the proposed initial scope, document access and ownership, source citations, policy version handling, permission boundaries, uncertain or conflicting results, and escalation when the documents do not support an answer. Identify dependencies and unresolved decisions without inventing facts about our systems or documents.

Propose a phased pilot and evaluation using representative complex cases. Distinguish finding an answer quickly from finding the correct, supported policy. Explain how to measure search effort, answer quality, and failure cases without inventing baselines or target values.

Return a concise recommendation, the proposed workflow, a phased plan, and the main risks and decisions needed before implementation. Preserve the decision against a customer-facing bot and keep all work at the planning level.
```

## Case 19

Replace “Your payment has failed” with “Payment unsuccessful”. Preserve the replacement text exactly and return only that text.

## Fresh case: Evenings

### Need interpretation

You want practical help reclaiming your evenings because you keep working late. The cause is unknown, so the prompt should support a useful first experiment without assuming whether workload, expectations, or work habits are responsible.

### Optimized prompt

```text
Help me reclaim my evenings. I keep working late and want a practical way to finish work earlier.

Do not ask questions. Work with this limited context and keep any assumptions explicit. Do not presume that the cause is poor discipline or that I can freely change my workload or working hours.

Give me a small, realistic one-week experiment: a short way to notice what keeps work running late, a simple end-of-day routine, and concrete responses to unfinished work or late requests. Distinguish actions I can try independently from changes that may require agreement with other people. Make suggestions adaptable to my actual schedule without inventing a finishing time or personal circumstances.

Keep the plan manageable. Include a brief way to review whether I regained evening time and whether essential work suffered, then explain how to adjust based on what happened. Use direct, supportive language and avoid generic productivity advice or promises.
```

## Fresh case: Make this better

### Need interpretation

The material to improve is missing, so the task cannot yet be identified reliably.

### Provisional optimized prompt

```text
Improve the following material while preserving its intended meaning and any stated constraints:

[Paste the material to improve]

Use the material and its context to choose proportionate improvements. Preserve factual content, avoid unsupported additions, and return the improved version with a brief explanation of the significant changes. If an ambiguity would materially change the result, identify it instead of silently choosing a different purpose.
```

### Follow-up questions

1. What text or other material does “this” refer to? This determines what needs improvement and makes a task-specific refinement possible.
