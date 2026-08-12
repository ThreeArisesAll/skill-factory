<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Skill Factory packages reusable Codex workflows for prompt refinement, task handoff, and spritesheet production">
</p>

<p align="center">
  <strong>Focused Codex skills with inspectable instructions, metadata, references, and tools.</strong><br>
  Pick one package, link it into your local skills directory, and invoke it by name.
</p>

## Start with a skill

Each top-level directory is an independent package. The package boundary keeps instructions, interface metadata, references, scripts, and assets together so a workflow can be reviewed or adapted without treating it as a black box.

| Skill | Use it when you need to… | Invoke |
| --- | --- | --- |
| [`refine-prompts`](./refine-prompts/) | Turn a rough request into one copy-ready prompt without executing the underlying task | `$refine-prompts` |
| [`handoff-next-task`](./handoff-next-task/) | Compress verified context into exactly one actionable, non-review Codex task and confirm that it starts | `$handoff-next-task` |
| [`create-better-spritesheet`](./create-better-spritesheet/) | Design, assemble, validate, or integrate a contract-matched 2D character spritesheet | `$create-better-spritesheet` |

## Quick start

From this repository root, link the package you want into a local Codex installation that loads skills from `~/.codex/skills`:

```bash
mkdir -p ~/.codex/skills
ln -s "$PWD/refine-prompts" ~/.codex/skills/refine-prompts
```

Replace `refine-prompts` with another package name as needed. The command intentionally fails if that destination already exists; inspect the existing entry before replacing it.

Then invoke the installed skill explicitly:

```text
Use $refine-prompts to turn this rough request into one ready-to-use prompt: …
```

```text
Use $handoff-next-task to package the current work and start one concrete next task.
```

```text
Use $create-better-spritesheet to create a contract-matched walk cycle from these references: …
```

## Package anatomy

```text
<skill-name>/
├── SKILL.md              # Invocation contract and workflow
├── agents/
│   └── openai.yaml       # User-facing name, description, and default prompt
├── references/           # Optional branch-specific guidance
├── scripts/              # Optional deterministic tools
└── assets/               # Optional source or reference material
```

`SKILL.md` is the source of truth. Detailed material stays behind relative links, while package-specific implementation remains inside its owning directory.

## Spritesheet toolkit

`create-better-spritesheet` is the most implementation-heavy package in the repository. Its workflow connects action-reference intake, identity locking, motion design, frame production, assembly, mechanical validation, and optional runtime integration.

| Tool | Responsibility |
| --- | --- |
| [`assemble_spritesheet.py`](./create-better-spritesheet/scripts/assemble_spritesheet.py) | Assemble ordered RGBA frames into a row-major or column-major grid and emit clip metadata |
| [`validate_spritesheet.py`](./create-better-spritesheet/scripts/validate_spritesheet.py) | Validate layout, alpha integrity, safe bounds, loop closure, and optional motion profiles |
| [`build_idle_spritesheet.py`](./create-better-spritesheet/scripts/build_idle_spritesheet.py) | Build the specialized planted breathing loop from an approved transparent source |
| [`prepare_optical_candidate.py`](./create-better-spritesheet/scripts/prepare_optical_candidate.py) | Normalize and compare target-size optical correction candidates |
| [`add_silhouette_outline.py`](./create-better-spritesheet/scripts/add_silhouette_outline.py) | Add a deterministic outer silhouette stroke to a canonical source frame |
| [`image_utils.py`](./create-better-spritesheet/scripts/image_utils.py) | Provide shared premultiplied-alpha image operations |

The package also includes a real [walk-cycle reference](./create-better-spritesheet/assets/walk-cycle-reference.png) and focused contracts for motion, optical sizing, quality, reference search, silhouette treatment, and runtime integration.

## Develop and validate

There is no repository-wide build system. Documentation-only packages should be checked for valid YAML/frontmatter, working relative links, matching package and frontmatter names, and English-only package content.

The image tools require Python 3.10+, NumPy, and Pillow. Use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/pip install numpy Pillow
.venv/bin/python create-better-spritesheet/scripts/assemble_spritesheet.py --help
.venv/bin/python create-better-spritesheet/scripts/validate_spritesheet.py --help
```

For a real change, exercise the success path and failure behavior with representative RGBA fixtures, inspect generated frames at native size, and validate against explicit frame dimensions and counts:

```bash
.venv/bin/python create-better-spritesheet/scripts/validate_spritesheet.py \
  --sheet <sheet.png> \
  --frame-width 96 \
  --frame-height 96 \
  --frame-count 8
```

## Add or change a package

1. Keep the package in its own lowercase kebab-case directory.
2. Make the `name` in `SKILL.md` match the directory exactly.
3. Write all package instructions, examples, placeholders, script messages, and `agents/openai.yaml` metadata in English.
4. Keep the main workflow concise and link detailed branches through relative Markdown paths.
5. Validate the behavior the package actually promises; scripts should cover help, success, invalid input, metadata, and validator failures where applicable.
6. Keep generated output, virtual environments, caches, and unrelated changes out of the package.

## Repository boundaries

- Packages are versioned together but invoked independently.
- Python dependencies apply to the spritesheet tools, not to the documentation-only skills.
- No repository-wide test runner or dependency manifest is currently configured.

## License

This repository and its skill packages are available under the [MIT License](./LICENSE).
