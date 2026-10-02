# Independent qualitative paired review

**Preference: after, slight margin.** The follow-up fixes the targeted implementation-branch verification omissions and optional-resource question in the actual common outputs. It also makes diagnostic readiness more coherent in the package instructions. The contrast outputs preserve missing-evidence and binding-resource boundaries, including the no-questions conflict case. No blocking regression is demonstrated.

The improvement is not uniform across the package. Several common outputs already behaved well before; their new wording is not evidence of a relative gain. Some unnecessary framing returns, and the marketing output loses a useful current-source requirement. The confidence here concerns the observed prompt contracts, not downstream execution.

## Review scope

I read before first, then after, the supplied package materials, the respective outputs, and judge-rubric.md. I compared the 27 common cases. Cases 28–31 are after-only contrast coverage and are not included as relative improvements. I used the rubric qualitatively, without numerical scores, and did not read other reports or execute the generated prompts.

## Targeted questions

| Question                                                  | Finding and evidence                                                                                                                                                                                                                                                                                                          |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Is diagnostic readiness consistent?                       | Resolved at the instruction level and consistent in the observed examples. The new readiness rule evaluates the next deliverable and the discovery reference now points to it. After 12 and 17 are explicitly bounded plans whose unknown findings remain unknown. They do not promise a factual diagnosis or final selection |
| Are conditional implementation checks present?            | Yes in common cases 11 and 25. Each implementation branch now names affected layout, the relevant user journey, actual results, and unverified checks. Before supplied a selected artifact but omitted corresponding implementation verification                                                                              |
| Is optional-resource questioning removed?                 | Yes in common case 2: after asks about product, audience, and objective, while budget/team variation is handled inside the prompt. The optional execution-constraints placeholder and resource question are gone                                                                                                              |
| Does this weaken missing-evidence boundaries?             | No observed weakening. Common cases 3, 10, 24, and 26 still expose indispensable sources or candidates. Contrast case 28 retains the log-based final selection and withholds a winner without logs                                                                                                                            |
| Does this erase binding resource requirements?            | No in contrast case 30. The exact staffing commitment remains provisional; hours, demand, and capacity must be established, and scenarios are not substituted. Common case 27 remains a clearly conditional rough estimate                                                                                                    |
| Are design-only checks distinguished from runtime checks? | Yes. Common 11 and 25 review their design/specification artifacts and label later implementation checks as proposed. Contrast 29 adds concrete mockup-to-handoff consistency review and separately proposed signup-flow testing                                                                                               |
| Are no-question conflicts handled?                        | Yes in contrast 31: both outer response and generated prompt avoid questions, keep the impossible constraint combination visible, and withhold a supposedly compliant summary. Common 10, 17, 20, and 27 also retain no-questions                                                                                             |

## Demonstrated relative gains

**Cases 11 and 25 provide the strongest behavioral improvement.** After includes verification within each conditional implementation branch rather than relying on general acceptance wording elsewhere. For the homepage, it checks relevant screen sizes and the homepage-to-registration journey; for the dashboard, it checks the layout and the journey from information review to the supported decision action. The reporting contract distinguishes actual results from unavailable checks. These are actionable checks for the selected work, not ornamental mentions of testing.

The design branches also improve precision. Case 11 asks the downstream agent to review hierarchy and coverage of screen sizes/states in the proposal itself. Case 25 checks the specification against intended decisions. Both distinguish those artifact reviews from future software tests. This preserves the ability to verify design-only work without claiming that a working registration flow or dashboard has been tested.

**Case 2 removes a redundant resource request.** Before simultaneously allowed conditional resource estimates and asked about budget, people, and timeframe. After reserves its three questions for the unknown product, audience, and marketing outcome, with a lean-to-scaled approach for resources. It still refuses to manufacture a tailored strategy before the actual app and objective are supplied. This is a real clarification-efficiency improvement.

**Case 12 is clearer about the immediate deliverable.** Before led with diagnosis and an action plan and allowed a further evidence question. After asks for a diagnostic/intervention plan and specifies a small evidence-gathering step where data is absent. It therefore has a complete plan contract even when factual diagnosis is unavailable. This narrows the readiness claim to work that can be completed now, while leaving the final intervention dependent on evidence.

**The package-level readiness conflict is reduced.** Before's discovery reference could direct a provisional label simply because intervention choice remained unresolved or questions were forbidden, while its outputs 12 and 17 were already copy-ready diagnostic plans. After centralizes the distinction and removes those competing reference instructions. That improves maintainability and explains the observed behavior consistently. It is not a newly demonstrated output gain in case 17: before already honored no-questions and withheld an unsupported bot choice.

## Remaining defects, losses, and reservations

- **Case 2 weakens sourcing for changing recommendations.** Before required current cited sources for changing external facts informing recommendations. After only says to identify market claims needing verification before execution. A marketing plan may itself contain current platform or market recommendations, so deferring verification to execution can leave the requested plan inadequately supported. This does not undo the resource-question fix, but it is a concrete conditional robustness loss and merits restoring the source requirement.
- **Case 25 partly presupposes an information gap.** Its required placeholder asks for the decisions and “the information currently missing,” and its first question asks what prevents the decision today. The stated observation is indecisive meetings, not proven missing information or a known cause. The later ownership/authority branch helps, but the input contract should permit “cause unknown/no established information gap” without making the user diagnose the meeting first. This is a small intent-calibration issue rather than a complete task substitution.
- **Case 17 could be more explicit about evidence access.** Before conditionally referenced existing support records and said to describe a review if records could not be accessed. After says to “identify existing evidence” while also declaring that only support overload is supplied and forbidding invented systems/findings. A capable downstream agent can read this as evidence categories, but “identify evidence that could be available” would be more consistent. No fabricated access is present in the actual output.
- **Simple outputs regain repeated interpretation text.** After cases 5, 7, 8, and 20 add introductory framing that before omitted. Some is useful, but in cases 5 and 8 it largely repeats the first line of the prompt. The follow-up is not an across-the-board concision improvement.
- **The readiness rule still requires judgment.** “Cannot be completed reliably” does not mechanically determine when a generic answer would underdeliver a specifically requested result. The explicit prohibition on replacing final selection or implementation with a plan is important. The contrast cases demonstrate the correct boundary here, but do not establish reliability for subtler requests.

None of these is a blocking regression on the supplied cases. The actual outputs do not perform unauthorized execution, invent source evidence, violate a no-questions instruction, or declare an unsupported final purchase/staffing decision.

## Common-case assessment

Pass means the supplied refinement adequately handles the request. Partial identifies a concrete contract weakness; it does not mean a downstream task was executed and failed.

| Case | Before  | After                 | Paired observation                                                                     |
| ---- | ------- | --------------------- | -------------------------------------------------------------------------------------- |
| 1    | Pass    | Pass                  | Product facts, price, format, and unsupported-benefit limits retained                  |
| 2    | Partial | Partial               | After fixes optional resource questioning but weakens current-source handling          |
| 3    | Pass    | Pass                  | Missing transcript blocks findings and quotations; capacity stays conditional          |
| 4    | Pass    | Pass                  | Exact label, narrow local edit, proportionate check, no commit/push                    |
| 5    | Pass    | Pass                  | General comparison remains planning-only; after adds current-source handling           |
| 6    | Pass    | Pass                  | Missing spec remains visible; scoped implementation/tests and updates retained         |
| 7    | Pass    | Pass                  | Current API verification and host/model separation; future tests are proposed          |
| 8    | Pass    | Pass                  | Read-only correctness review with conditional delegation and evidence                  |
| 9    | Pass    | Pass                  | Explicit reusable input slot and source/instruction separation                         |
| 10   | Pass    | Pass                  | Missing interview remains provisional without asking questions                         |
| 11   | Partial | Pass                  | After includes verification in implementation branch and real design-artifact review   |
| 12   | Pass    | Pass                  | After clarifies bounded planning readiness; factual intervention remains unresolved    |
| 13   | Pass    | Pass                  | Fixed chatbot choice and planning scope; checks remain proposed                        |
| 14   | Pass    | Pass                  | Unfilled priority cannot silently select a summary branch                              |
| 15   | Pass    | Pass                  | Supplied pricing decision and current evidence preserved                               |
| 16   | Pass    | Pass                  | Both metrics evaluated and proposed roles distinguished from user decisions            |
| 17   | Pass    | Pass                  | Both honor no-questions and support conditional planning rather than bot selection     |
| 18   | Pass    | Pass                  | Supplied workload evidence used and rejected customer-facing bot retired               |
| 19   | Pass    | Pass                  | Exact strings and output-only constraints retained                                     |
| 20   | Pass    | Pass                  | Conditional, reversible evening-protection advice without invented diagnosis           |
| 21   | Pass    | Pass                  | Missing object and desired outcome remain explicit                                     |
| 22   | Pass    | Pass                  | Teacher-upload context recovered with simple recovery and no invented cause            |
| 23   | Pass    | Pass                  | Quoted injection stays data and two-sentence deliverable retained                      |
| 24   | Pass    | Pass                  | Missing candidate ideas remain provisional; no impossible model guarantees             |
| 25   | Partial | Pass with reservation | After fixes implementation checks; information-gap placeholder is slightly presumptive |
| 26   | Pass    | Pass                  | Final artwork waits for approved material/specifications and verifies actual export    |
| 27   | Pass    | Pass                  | Scenario estimate remains usable without optional inputs or headcount commitment       |

## Contrast coverage only

- **28: Pass.** Missing logs block the explicitly requested log-based vendor selection. It does not replace selection with diagnosis, asks no questions, requires current vendor evidence later, and distinguishes recommendation from purchase authorization. Even after logs arrive, unresolved binding requirements can still block a winner.
- **29: Pass.** Both delivery choices and the missing mockup remain visible. Implementation checks cover responsive layout, signup validation and supported completion/error states. Design-only work checks handoff consistency and proposes future runtime checks. No-publishing is preserved.
- **30: Pass.** Exact staffing cannot be produced from unknown demand/hours without assumptions. The response keeps it provisional, asks for genuine workload/capacity inputs, checks units and coverage, and avoids claiming booking or approval. The date/schedule question is broad, but the calendar interpretation has practical relevance to an exact commitment.
- **31: Pass.** Future report input is a legitimate template slot; the unresolved conflict is not. The prompt forbids questions and unauthorized relaxation, rejects unrealistic speaking-rate tricks, and allows only independent availability/conflict work until the requirements become feasible.

## Limits

The evidence is one supplied output per common case and four after-only contrast outputs. There are no repeated generations, real downstream tasks, or tests with actual repositories, transcripts, staffing operations, print exports, or API harnesses. The package changes and contrast cases closely target the known issues, so performance on other ambiguity patterns, languages, or lengthy conversations is unproven. External model documentation was not verified. The narrow conclusion is that the follow-up materially improves these observed prompt contracts while retaining the tested boundaries; it does not establish general perfection or downstream success.
