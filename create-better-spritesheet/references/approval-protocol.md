# Approval Protocol

Use this protocol for every user or reviewer gate in canonical, motion, sequence, and integration work. A gate is valid only when all five properties below are satisfied.

Treat canonical, motion-blueprint, keyframe-set, spacing-plan, sequence, and package review as distinct gates. Completion of one never substitutes for another; dependency order controls when each may open. A gate may open only after its subject passes every owning machine check and required agent preflight. A known visual hard blocker makes the subject ineligible for presentation or approval.

## Authority

Identify who can approve the subject before requesting a decision. Use the user as the default authority. Accept repository policy, an attached decision record, or a named delegate only when the user or authoritative project rules grant that authority for the exact subject.

Reuse an already resolved decision when its subject and bound inputs are unchanged. Ask only when authority is absent, evidence conflicts, or a material choice remains unresolved.

## Presentation

Present one complete current approval subject with:

- A stable gate name and revision
- The full ordered subject, not a partial diff
- Material assumptions and unresolved consequences
- Exact hashes for byte-bound image gates
- A direct request to approve the current revision or request changes

For visual gates, present the complete evidence set together at a comparable scale and preserve any required native-pixel inspection. Do not omit a required background, resolution, or bound subject. For plan gates, present every item and relationship governed by the decision. A recommendation may accompany the subject but cannot replace the explicit decision.

Withhold a visual approval question when preflight finds a white fringe, jagged step, directional thickness spike, square corner, outline bulge, or temporal outline flicker. Route the defect to its owning source, Alpha policy, outline contract, or renderer; regenerate the complete affected presentation and machine evidence before the gate may open.

## Pause

Pause every dependent production action while a material gate is unresolved. Continue only work that cannot alter or presuppose the pending subject. In particular:

- Pause motion image generation until both the canonical and motion blueprint are approved.
- Pause in-between generation until the keyframe set and spacing plan are approved.
- Pause package building until canonical, keyframe-set, and sequence approvals bind current bytes.
- Pause delivery sealing until package review binds the exact verified package, diagnostics, and complete presentation.
- Pause production replacement until integration authority is explicit.

Silence, discussion, approval of selected items, or approval of an earlier revision does not complete the gate.

## Invalidation

Invalidate an approval when its presented subject, bound bytes, governing contract, admission proof, ordering, or material assumption changes. Invalidate every dependent approval and output transitively. Recompute the complete current subject, increment its revision, present it again, and request a new decision.

Do not reopen an unchanged upstream decision merely because a descendant changed. Route a defect to its owning stage so invalidation remains as narrow as the dependency graph permits.

## Serialization

Distinguish executable approval fields from the richer workflow ledger:

- Populate each closed executable approval object with exactly the fields its schema accepts. Store `canonical-approval`, `keyframe-set-approval`, and `sequence-approval` in `spritesheet-production-request/v4` and the resulting `spritesheet-package/v4` manifest as defined by the CLI.
- Record the gate name, revision, authority, full decision context, presentation subjects, and decision time when available in the applicable approval ledger or `review-packet/v1`. Do not add ledger or timestamp fields to a closed schema that does not accept them.
- Serialize identity, motion, spacing, diagnostic, review-presentation, and runtime-playback evidence through `spritesheet-production-delivery/v1` as defined in [production-delivery.md](production-delivery.md). Keep these records outside the closed v4 request and package schemas.
- Keep runtime replacement authority outside the pixel package manifest unless the target repository defines its own authoritative record.

Classify a recorded human decision as `REVIEWED`. Classify schema, hash, binding, geometry, and replay checks as `MACHINE-VERIFIED`. Classify metadata meaning and claims about generative model inputs or obedience as `DECLARED` unless a human review explicitly covers them. Classify externally produced runtime evidence as `SUPPLIED`; verification may check its schema, hashes, bindings, assets, and recorded check results without claiming direct observation of the runtime.
