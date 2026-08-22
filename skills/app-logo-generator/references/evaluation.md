# Candidate Evaluation and App-context Testing

Use this reference during convergence and validation. The matrix structures discussion; it does not choose the final mark.

## Hard Gates

Resolve these before weighted scoring:

1. **Platform viability:** the semantic core survives required masks, layers, backgrounds, and sizes.
2. **Critical small-size viability:** the candidate does not collapse into an ambiguous blob at its required minimum size.
3. **Severe semantic or cultural risk:** no known high-severity reading conflicts with the product or target market.
4. **Obvious similarity risk:** no unresolved close resemblance to a known mark in the relevant category or market.
5. **Safety or regulatory risk:** the mark does not make a prohibited, deceptive, or safety-critical claim.

These are screening gates, not certificates. Platform screenshots do not prove platform approval, and a similarity search does not provide legal clearance.

## Weighted Diagnostic Matrix

Score applicable criteria from 1 to 5 and record one sentence of evidence for every score. For a new app, mark brand continuity `N/A` and renormalize the remaining weights rather than awarding free points.

| Criterion | Default weight | 1 | 3 | 5 |
|---|---:|---|---|---|
| Problem fit | 20 | Weak relation to the brief | Solves part of the problem | Directly resolves the main recorded failures |
| Distinctiveness and recognition | 15 | Easily confused | Some ownable features | Quickly recognizable with a stable unique feature |
| Small-size performance | 15 | Core structure disappears | Needs a special small-size treatment | Core structure remains clear at required sizes |
| Platform and container fit | 15 | Fails common masks or contexts | Works with exceptions | Stable across required platform contexts |
| Brand continuity | 10 | Discards useful equity without cause | Retains some value | Precisely preserves or reinterprets proven equity |
| Semantic and cultural robustness | 10 | High-risk misreading | Understandable but unverified | Stable in the priority markets tested |
| Production stability | 10 | Depends on fragile conditions | Has manageable exceptions | Can be reproduced correctly with few rules |
| System-generating capacity | 5 | Isolated mark only | Supports a few extensions | Supplies a reusable visual grammar |

For applicable criteria:

```text
normalized score = sum(score / 5 * weight) / sum(applicable weights) * 100
```

Interpret close totals as a prompt to inspect the evidence, not as mathematical precision. If a designer scores small-size performance as 5 and an engineer scores it as 2, test the actual asset instead of averaging the disagreement away.

## Required Evidence Per Candidate

- a concept card;
- source SVG or intentionally chosen raster master;
- the recognition invariant;
- hard-gate status;
- weighted matrix with evidence notes;
- a board or screenshots at relevant real sizes and surfaces;
- unresolved legal, cultural, technical, or user-validation risk.

## First-pass Visual Checks

Use `../scripts/build_icon_test_board.py` for a consistent board, then inspect:

- **16–128 px range:** identify where counters, gaps, strokes, or secondary forms disappear.
- **Masks:** check circle, rounded-square, and squircle-like crops; keep the semantic core inside the current safe region.
- **Backgrounds:** white, near-black, saturated color, transparency checker, and representative wallpaper or UI.
- **Badge:** verify that a notification badge does not hide the identifying feature or lose contrast.
- **Crowded field:** compare with real category and system icons; the generated synthetic field is only a proxy.
- **Reduced color:** verify silhouette and structure without relying entirely on brand color.

Do not treat a large isolated mockup as evidence for any of these properties.

## Recognition and Findability Test

When the claim matters, use a small protocol rather than asking “Do you like it?”:

1. Define the target surface and participant group.
2. Show a representative crowded screen for a fixed short interval.
3. Ask participants to find the app, then remove the screen.
4. Measure time, incorrect selections, and whether the participant can describe or re-find the icon.
5. Compare candidates under the same conditions.

Record the sample, environment, and uncertainty. A small informal test is directional evidence, not a population estimate.

## Semantic and Cultural Check

In each priority market, ask neutral questions:

- What does this shape look like first?
- What organization, object, action, belief, hazard, or political symbol does it recall?
- What does it suggest the app does?
- Is any association offensive, misleading, or unsafe?

Do not lead participants with the intended story. Low-confidence or high-severity results require local review.

## Accessibility Boundary

A brand mark is not automatically subject to a universal text-contrast threshold. Functional icons and graphical objects needed to understand or operate the UI are a different category and may carry contrast requirements. Verify current accessibility standards for the actual use; do not transfer an exemption or requirement from one context to another.

## Validation Claims

Report separately:

- static or scripted checks;
- local visual inspection;
- real-device/platform checks;
- participant or stakeholder review;
- legal/cultural specialist review;
- store experiment or post-launch production evidence.

Skipped checks and empty samples are not passing evidence.
