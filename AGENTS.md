# Repository Guidelines

## Project Structure & Module Organization

Each top-level, kebab-case directory is a standalone Codex skill package. `SKILL.md` defines invocation and workflow behavior; `agents/openai.yaml` contains user-facing metadata. `create-better-spritesheet/` also owns reusable Python CLIs in `scripts/` and branch-specific guidance in `references/`. Keep detailed material behind relative Markdown links from `SKILL.md`, and keep package-specific code and documentation inside that package.

## Build, Test, and Development Commands

There is no repository-wide build system or dependency manifest. The image tools require Python 3.10+, NumPy, and Pillow. Use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/pip install numpy Pillow
.venv/bin/python create-better-spritesheet/scripts/assemble_spritesheet.py --help
.venv/bin/python create-better-spritesheet/scripts/validate_spritesheet.py --help
```

Run a tool with real RGBA fixtures and contract values before submitting script changes. For example, invoke `validate_spritesheet.py --sheet <sheet.png> --frame-width 96 --frame-height 96 --frame-count 8`.

## Coding Style & Naming Conventions

**All in English:** Every skill package must use English throughout, including `SKILL.md`, `references/`, examples, placeholders, output templates, script messages, and `agents/openai.yaml`. A skill's frontmatter `name` must match its directory. Use kebab-case for packages and reference files, snake_case for Python modules and functions, and zero-padded names for ordered frame assets. Python uses four-space indentation, type hints, `pathlib.Path`, focused helpers, and a `main()` returning an exit code. YAML uses two-space indentation.

## Testing Guidelines

No automated test framework or coverage threshold is configured. For documentation changes, verify YAML/frontmatter syntax, relative links, and package-name consistency. For Python changes, exercise `--help`, success paths, invalid arguments, emitted metadata, and validator failures against representative fixtures; also inspect generated sprites at native size. If adding pytest coverage, place it under `tests/test_<module>.py` and add a reproducible dependency/runner definition.

## Commit & Pull Request Guidelines

Follow the repository's Conventional Commit history: `docs(skill): update prompt workflow` or `feat(create-better-spritesheet): add atlas validation`. Add an imperative bullet-list body for multi-part changes. Pull requests should state the affected skill, behavioral impact, validation commands and results, and linked issue. Include before/after images for visual pipeline changes. Keep unrelated edits separate, and avoid adding new `.DS_Store`, `__pycache__`, virtual environments, or generated outputs.
