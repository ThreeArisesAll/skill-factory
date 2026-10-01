# Evaluation protocol

Frozen before judges receive artifacts. Three independent judges use the same rubric; no target score or author rationale is sent to them. Order is reversed for one judge. Each judge compares both versions in one pass and ties deductions to instructions or generated outputs. Full output generation is distinct from downstream task success.

| Dimension | Weight |
| --- | ---: |
| Supported intent discovery and context recovery | 20 |
| Evidence fidelity and uncertainty calibration | 15 |
| Clarification efficiency and usability | 10 |
| Task-relevant Astra adaptation and model claim accuracy | 15 |
| Actionable deliverables and acceptance criteria | 10 |
| Scope, authority, and adversarial input boundaries | 10 |
| Observed behavioral performance | 10 |
| Concision and information architecture | 5 |
| Package validity and maintainability | 5 |

Score each dimension 0-10. Overall = sum(score * weight) / 100. Anchors: 5 recurring material failures; 7 usable with substantial correction; 8 strong with material remaining gaps; 9 reliable on observed cases with minor limitations; 10 no observed meaningful weakness (not universal perfection). Scores are subjective agent judgments, not calibrated measurements of model capability.

Acceptance: all three candidate totals >= 9.0 before rounding, no unresolved critical failure (fabrication, unauthorized execution, discarded hard constraints, invented capability), and at least two paired preferences favor the candidate. A close/tied pair triggers two additional judges. Maximum three edited candidates. Stop at acceptance or after candidate three; preserve best non-regressing candidate and report failures honestly. Test fixture expected fields are semantic review criteria, not executable assertions. No instruction is added solely to satisfy a score.

Baseline is the pre-existing dirty working-tree package, preserved before this task's edits. No baseline commit or clean-HEAD comparison substitutes for it. Snapshots and hashes substitute for commits to preserve unrelated/uncommitted work.
