# Asset Architecture and Delivery

Use this reference when turning a selected direction into production-ready assets.

## Recommended Package

Adapt the package to the user's scope; do not create empty placeholders.

```text
app-logo/
|-- brief.md
|-- decision-log.md
|-- concepts/
|   `-- direction-name.svg
|-- master/
|   |-- mark.svg
|   |-- mark-monochrome.svg
|   |-- mark-small.svg            optional optical correction
|   `-- wordmark.svg              when requested
|-- platform/
|   |-- ios/                      current required source assets
|   |-- android/                  foreground/background or monochrome layers
|   `-- stores/                   listing assets kept distinct from launcher assets
|-- validation/
|   |-- icon-test-board.html
|   |-- findings.md
|   `-- screenshots/              only actual evidence
`-- usage.md
```

## Source-master Rules

- Use a square coordinate system for app-icon source artwork and preserve an editable vector master when the design is vector-based.
- Keep shapes simple enough to survive optical correction and small-size variants.
- Use stable, descriptive layer or group names when the format supports them.
- Keep the recognition invariant consistent across variants.
- Remove accidental editor metadata, hidden objects, unused definitions, and external file references.
- Ensure SVG IDs are unique and references resolve.
- Avoid filters, masks, blend modes, or fonts that the target export pipeline cannot reproduce reliably.
- Convert essential type to outlines only in delivery copies; retain an editable licensed source when possible.
- Do not add a rounded-square clipping path merely to imitate an operating-system mask.
- Do not encode meaning only through color when the same asset is expected to work in monochrome or reduced-color contexts.

## Variant Architecture

Treat these as related but distinct design problems:

- **Master mark:** the canonical identifying form.
- **Launcher icon:** optimized for the device container and neighboring icons.
- **Store-listing icon:** optimized for store discovery and current listing rules.
- **Small or micro mark:** optical correction for contexts where the master loses structure.
- **Monochrome mark:** preserves the invariant without depending on brand color.
- **Appearance variants:** only where supported or required; keep their relationship explicit.
- **Adaptive layers:** foreground, background, and monochrome layers when the current Android workflow requires them.
- **Wordmark:** separately spaced and tested; do not force it inside the launcher icon unless the concept requires readable text at that size.

## Current-spec Verification

Before final export:

1. Identify the exact target operating-system and store versions.
2. Open current first-party platform documentation.
3. Record the retrieval date and direct source link in `usage.md` or `findings.md`.
4. Verify dimensions, color space, alpha rules, file format, size limits, masks, layer requirements, and naming conventions.
5. Export from the master, then inspect the exported files rather than assuming the tool preserved the source.

Do not copy platform dimensions from this Skill; omission is intentional because those values change.

## Export Checks

- expected pixel dimensions and file type;
- color profile and alpha behavior;
- no unintended baked corner radius or clipping;
- no missing font, external image, or linked resource;
- foreground/background alignment for layered assets;
- visual inspection at 100% and actual display size;
- deterministic filenames and a mapping from each file to its target surface;
- hash or file inventory when delivery integrity matters.

## Usage Note

Keep it short and operational:

- recognition invariant and minimum viable form;
- allowed color and background variants;
- spacing or safe-area guidance derived from actual tests;
- approved small-size correction;
- prohibited distortions or substitutions;
- owner and source-master location;
- current platform-spec sources and verification date;
- unresolved risks or checks still requiring human or specialist review.

## Evidence-aware Handoff

State what has actually been verified. Keep these separate:

- editable-source and static validation;
- visual review in generated test boards;
- real-device and store-context review;
- user recognition or market testing;
- stakeholder aesthetic approval;
- trademark or legal clearance;
- production performance after launch.

Never promote one category of evidence into another.
