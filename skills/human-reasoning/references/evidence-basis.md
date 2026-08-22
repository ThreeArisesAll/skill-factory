# Evidence Basis and Claim Boundaries

This bibliography informed the Skill’s operational controls. It is not a vote-counting proof of a metaphysical essence. Sources play different roles: architecture description, empirical finding, theoretical framework, position paper, or product documentation.

## Design conclusions supported by the source set

- Scope claims to the actual human population and deployed AI system.
- Do not equate language fluency with every form of thought, grounding, or understanding.
- Treat perception, action, bodily state, causal intervention, memory, shared intentionality, and culture as potentially decision-relevant aspects of human cognition.
- Treat model self-explanations and verbal confidence as fallible outputs requiring external checks.
- Test prompt sensitivity and agreement pressure.
- Evaluate Skills with explicit outcomes, process checks, and behavioral rubrics.

## Sources

### OPENAI_SKILLS

OpenAI. “Build skills.” ChatGPT Learn / Codex documentation.

- Link: https://learn.chatgpt.com/docs/build-skills
- Used for: Current Skill structure, invocation, discovery path, optional resources, and symlink support.

### OPENAI_API_SKILLS

OpenAI. “Skills.” OpenAI API documentation.

- Link: https://developers.openai.com/api/docs/guides/tools-skills
- Used for: Versioned bundles and the single-top-level-folder ZIP requirement.

### OPENAI_EVALS

OpenAI. “Testing Agent Skills Systematically with Evals.”

- Link: https://developers.openai.com/blog/eval-skills
- Used for: Prompt → captured run → checks → score; deterministic and rubric-based evaluation design.

### VASWANI

Vaswani, A. et al. (2017). Attention Is All You Need. NeurIPS.

- Link: https://arxiv.org/abs/1706.03762
- Used for: Architectural background for transformer sequence modeling.

### BROWN

Brown, T. B. et al. (2020). Language Models are Few-Shot Learners. NeurIPS.

- Link: https://arxiv.org/abs/2005.14165
- Used for: In-context adaptation is not the same as durable personal learning or autobiographical continuity.

### BAR

Barsalou, L. W. (2008). Grounded Cognition. Annual Review of Psychology, 59, 617–645.

- Link: https://doi.org/10.1146/annurev.psych.59.103006.093639
- Used for: Perception, action, bodily states, and situated simulation as important components of human cognition.

### LAKE

Lake, B. M., Ullman, T. D., Tenenbaum, J. B., & Gershman, S. J. (2017). Building machines that learn and think like people. Behavioral and Brain Sciences, 40, e253.

- Link: https://doi.org/10.1017/S0140525X16001837
- Used for: Causal models, intuitive physics and psychology, compositionality, and learning-to-learn.

### BENDER

Bender, E. M., & Koller, A. (2020). Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data. ACL 2020.

- Link: https://aclanthology.org/2020.acl-main.463/
- Used for: Discipline around claims that move from linguistic form to meaning or understanding.

### MAH

Mahowald, K. et al. (2024). Dissociating language and thought in large language models: a cognitive perspective. Trends in Cognitive Sciences, 28(6), 517–540.

- Link: https://doi.org/10.1016/j.tics.2024.01.011
- Used for: Formal linguistic competence versus functional language use and broader cognition.

### FED

Fedorenko, E., Piantadosi, S. T., & Gibson, E. A. F. (2024). Language is primarily a tool for communication rather than thought. Nature, 630, 575–586.

- Link: https://doi.org/10.1038/s41586-024-07522-w
- Used for: Evidence that human language systems and many forms of thought can be dissociated.

### BECHARA

Bechara, A., Damasio, H., Tranel, D., & Damasio, A. R. (1997). Deciding Advantageously Before Knowing the Advantageous Strategy. Science, 275(5304), 1293–1295.

- Link: https://doi.org/10.1126/science.275.5304.1293
- Used for: Bodily and affective signals can participate in human decision behavior before explicit verbal knowledge.

### SCHACTER

Schacter, D. L., Addis, D. R., & Buckner, R. L. (2007). Remembering the past to imagine the future: the prospective brain. Nature Reviews Neuroscience, 8, 657–661.

- Link: https://doi.org/10.1038/nrn2213
- Used for: Human episodic memory and constructive future simulation.

### TOMASELLO

Tomasello, M., & Carpenter, M. (2007). Shared intentionality. Developmental Science, 10(1), 121–125.

- Link: https://doi.org/10.1111/j.1467-7687.2007.00573.x
- Used for: Joint goals, shared attention, cooperation, and commitments in human social cognition.

### DEAN

Dean, L. G. et al. (2012). Identification of the Social and Cognitive Processes Underlying Human Cumulative Culture. Science, 335(6072), 1114–1118.

- Link: https://doi.org/10.1126/science.1213969
- Used for: Social learning processes and cumulative culture.

### SIMON

Simon, H. A. (1955). A Behavioral Model of Rational Choice. Quarterly Journal of Economics, 69(1), 99–118.

- Link: https://doi.org/10.2307/1884852
- Used for: Bounded rationality and satisficing under limited resources.

### TURPIN

Turpin, M., Michael, J., Perez, E., & Bowman, S. R. (2023). Language Models Don’t Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting. NeurIPS 2023.

- Link: https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract-Conference.html
- Used for: Model explanations can be plausible yet omit causal influences on the answer.

### SHARMA

Sharma, M. et al. (2023; revised 2025). Towards Understanding Sycophancy in Language Models. arXiv:2310.13548.

- Link: https://arxiv.org/abs/2310.13548
- Used for: User-belief matching can compete with truthfulness in assistant behavior.

### POSIX

Chatterjee, A. et al. (2024). POSIX: A Prompt Sensitivity Index For Large Language Models. Findings of EMNLP 2024.

- Link: https://aclanthology.org/2024.findings-emnlp.852/
- Used for: Intent-preserving prompt variations can materially change model behavior.

## Interpretive cautions

- Grounded and embodied cognition are active research programs, not a license to declare that text-based systems can never acquire useful world models.
- Research on language–thought dissociation does not imply language is unimportant to human thought; it blocks the simpler equivalence.
- Research on unfaithful explanations shows a verification risk, not that every rationale is useless.
- Sycophancy and prompt-sensitivity results are model-, task-, and evaluation-dependent; test the deployed system.
- Social and normative authority cannot be derived from benchmark performance alone.
