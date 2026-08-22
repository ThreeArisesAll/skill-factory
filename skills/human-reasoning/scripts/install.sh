#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="human-reasoning"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
CANON_ROOT="${HOME}/.agents/skills"
COMPAT_ROOT="${HOME}/.codex/skills"
TARGET="${CANON_ROOT}/${SKILL_NAME}"
COMPAT="${COMPAT_ROOT}/${SKILL_NAME}"
STAMP="$(date +%Y%m%d-%H%M%S)-$$"

resolve_path() {
  python3 - "$1" <<'PY_RESOLVE'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY_RESOLVE
}

backup_path() {
  local path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    local backup="${path}.backup-${STAMP}"
    mv "$path" "$backup"
    printf 'Backed up %s -> %s\n' "$path" "$backup"
  fi
}

mkdir -p "$CANON_ROOT" "$COMPAT_ROOT"

if [[ -d "$TARGET" ]] && [[ "$(resolve_path "$TARGET")" == "$(resolve_path "$SOURCE_DIR")" ]]; then
  printf 'Source is already the canonical install: %s\n' "$TARGET"
else
  backup_path "$TARGET"
  cp -R "$SOURCE_DIR" "$TARGET"
  printf 'Installed canonical skill: %s\n' "$TARGET"
fi

if [[ -L "$COMPAT" ]] && [[ "$(resolve_path "$COMPAT")" == "$(resolve_path "$TARGET")" ]]; then
  printf 'Compatibility symlink already correct: %s -> %s\n' "$COMPAT" "$TARGET"
else
  backup_path "$COMPAT"
  ln -s "$TARGET" "$COMPAT"
  printf 'Created compatibility symlink: %s -> %s\n' "$COMPAT" "$TARGET"
fi

python3 "$TARGET/scripts/doctor.py" --installed

printf '\nInstalled Human Reasoning Bridge v%s\n' "$(cat "$TARGET/VERSION")"
printf 'Canonical: %s\n' "$TARGET/SKILL.md"
printf 'Compatible: %s -> %s\n' "$COMPAT" "$TARGET"
printf 'Invoke in Codex with: $human-reasoning\n'
printf 'Restart Codex if the updated skill is not visible immediately.\n'
