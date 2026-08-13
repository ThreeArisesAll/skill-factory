# Repository Guidelines

## Project Structure & Module Organization

Each top-level, kebab-case directory is a standalone Codex skill package. `SKILL.md` defines invocation and workflow behavior; `agents/openai.yaml` contains user-facing metadata. `create-better-spritesheet/` also owns reusable Python CLIs in `scripts/` and branch-specific guidance in `references/`. Keep detailed material behind relative Markdown links from `SKILL.md`, and keep package-specific code and documentation inside that package.

## Build, Test, and Development Commands

There is no repository-wide build system or dependency manifest. The image tools require Python 3.10+, NumPy, and Pillow. Use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/pip install numpy Pillow
.venv/bin/python create-better-spritesheet/scripts/spritesheet_pipeline.py --help
```

Run the public pipeline with real RGBA fixtures and v4 production request files before submitting script changes. Canonical authoring requests and evidence remain v3, and canonical admission proofs remain v1. Exercise `prepare-canonical`, `build-package`, and `verify-package`; keep lower-level raster helpers internal to the package. Run the package regression suite with `python -m unittest discover -s create-better-spritesheet/tests -p 'test_*.py' -v` inside the isolated environment.

## Coding Style & Naming Conventions

**All in English:** Every skill package must use English throughout, including `SKILL.md`, `references/`, examples, placeholders, output templates, script messages, and `agents/openai.yaml`. A skill's frontmatter `name` must match its directory. Use kebab-case for packages and reference files, snake_case for Python modules and functions, and zero-padded names for ordered frame assets. Python uses four-space indentation, type hints, `pathlib.Path`, focused helpers, and a `main()` returning an exit code. YAML uses two-space indentation.

## Testing Guidelines

The spritesheet package uses Python `unittest`; no coverage threshold is configured. For documentation changes, verify YAML/frontmatter syntax, relative links, and package-name consistency. For Python changes, exercise `--help`, success paths, invalid arguments, emitted metadata, and validator failures against representative fixtures; also inspect generated sprites at native size. Place additional tests under `tests/test_<module>.py` and keep the isolated dependency command reproducible.

## Commit & Pull Request Guidelines

Follow the repository's Conventional Commit history: `docs(skill): update prompt workflow` or `feat(create-better-spritesheet): add atlas validation`. Add an imperative bullet-list body for multi-part changes. Pull requests should state the affected skill, behavioral impact, validation commands and results, and linked issue. Include before/after images for visual pipeline changes. Keep unrelated edits separate, and avoid adding new `.DS_Store`, `__pycache__`, virtual environments, or generated outputs.
