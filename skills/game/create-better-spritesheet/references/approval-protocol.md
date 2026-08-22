# Approval Protocol

An approval gate is valid only when its input is eligible, its complete subject is presented, the named authority explicitly approves that exact revision, and every bound hash or semantic dependency remains current.

## Current gates

| Gate | Eligible input | Complete approval subject | Continue only when | Invalidated by |
| --- | --- | --- | --- | --- |
| Canonical | Prepared views and replayed admission proofs | All required direction-camera views, six review composites per view, and identity contract | Exact complete view set is approved | Canonical bytes, view binding, identity contract, Alpha or outline policy, admission proof |
| Motion plan | Approved canonical set and action evidence or written-design authority | Entire `motion-plan/v2`, all clips, directions, and logical positions | Exact complete plan is approved | Any clip or position content, order, timing, event, role, view, topology, or plan assumption |
| Keyframe set | Approved motion plan and admitted planned keyframe sources | All current keyframes for the batch with exact source hashes | Entire set is approved | Any keyframe byte, source admission, canonical, or motion-plan change |
| Sequence | Approved keyframes and admitted planned in-betweens | Complete ordered logical sequence, including aliases, timing, and events | Entire sequence is approved | Any concrete source, alias, order, duration, event, plan, or upstream approval change |
| Package | Verified v5 package and complete diagnostic presentation | Identity, motion plan, package, diagnostics, native-size board, onion skin, contact sheet, and previews | Every required subject has one acceptable observation | Subject hash, diagnostic asset, package replay, quality policy, or presentation change |

## Present and pause

Present the full current subject, not a diff or selected subset. Include its stable gate, revision, material assumptions, unresolved consequences, and exact hashes where the checkpoint provides them. Ask for approval or requested changes.

Pause all dependent work while a gate is unresolved. In particular, produce or accept no motion image before motion-plan approval, build no package before sequence approval, and seal no delivery before package approval. Silence, discussion, or approval of a prior revision is not approval.

Withhold a visual approval question when a known hard blocker exists. Correct the owner, regenerate the complete affected presentation, and then open the gate. Do not ask a person to approve something the machine contract already rejects.

## Reuse and invalidation

Reuse an unchanged upstream approval. Do not ask again merely because a descendant changed. Conversely, invalidate transitively when the approved subject or a bound input changes. A revised motion plan always requires presentation and explicit approval of the complete revised plan before any image work resumes.

When a generated source deviates from the approved plan, choose one explicit path:

1. Reject or regenerate the source under the unchanged plan; or
2. Revise the plan, invalidate all image descendants, present the complete revision, and obtain new approval.

Never silently reinterpret an approved plan to fit generated output.

## Response contract

The current checkpoint's `response_schema` is the executable response contract. Copy its `checkpoint_id`, `job_revision`, and `context_sha256`; provide only the requested input or decision fields. A stale or malformed response must leave committed state unchanged.

Human approval is `REVIEWED`. Hashes, schemas, replay, geometry, and deterministic measurements are `MACHINE-VERIFIED`. Intended pose meaning, generator obedience, and metadata semantics are `DECLARED` unless a review explicitly covers them. External runtime evidence is `SUPPLIED` until independently observed under the target system.
