#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="human-reasoning"
TARGET="${HOME}/.agents/skills/${SKILL_NAME}"
COMPAT="${HOME}/.codex/skills/${SKILL_NAME}"
STAMP="$(date +%Y%m%d-%H%M%S)-$$"

resolve_path() {
  python3 - "$1" <<'PY_RESOLVE'
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY_RESOLVE
}

if [[ -L "$COMPAT" ]] && [[ "$(resolve_path "$COMPAT")" == "$(resolve_path "$TARGET")" ]]; then
  rm "$COMPAT"
  printf 'Removed compatibility symlink: %s\n' "$COMPAT"
elif [[ -e "$COMPAT" || -L "$COMPAT" ]]; then
  printf 'Left %s untouched because it is not the expected compatibility symlink.\n' "$COMPAT"
fi

if [[ -d "$TARGET" ]]; then
  BACKUP="${HOME}/.agents/skills/.human-reasoning-uninstalled-${STAMP}"
  mv "$TARGET" "$BACKUP"
  printf 'Moved canonical skill to recoverable backup: %s\n' "$BACKUP"
else
  printf 'No canonical skill found at %s\n' "$TARGET"
fi
