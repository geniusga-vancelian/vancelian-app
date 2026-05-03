#!/usr/bin/env bash
# Affiche le prompt Cursor « session bring-up Arquantix » (après reboot).
# Usage : bash scripts/cursor_prompt_arquantix_bringup.sh
#         bash scripts/cursor_prompt_arquantix_bringup.sh | pbcopy   # macOS : copier dans le presse-papiers
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILE="$REPO_ROOT/docs/arquantix/prompts/SESSION_BRINGUP_AFTER_REBOOT.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Fichier manquant : $PROMPT_FILE" >&2
  exit 1
fi
exec cat "$PROMPT_FILE"
