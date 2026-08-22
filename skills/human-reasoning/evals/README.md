# Live Evaluation Fixtures

Static validation proves that files, iteration records, matrices, and test definitions are internally consistent. It does not evaluate the target model.

Follow this live workflow:

1. Select the exact model, host, tool configuration, and Skill version.
2. Run `trigger-prompts.csv` to measure invocation precision and recall.
3. Run `behavior-prompts.jsonl` and capture final output, tool trace, sources, and artifacts.
4. Score each run with `references/eval-rubric.md` and its case-specific must/must-not checks.
5. Repeat framing-sensitive cases with neutral paraphrases and option-order changes.
6. Record regressions by track and add the smallest targeted iteration rather than rewriting the whole Skill.

OpenAI’s recommended pattern is prompt → captured run → checks → score. A useful result therefore includes the prompt, host configuration, trace or artifact, grader output, and release comparison—not merely “the prompt looks better.”
