#!/usr/bin/env bash
# H1: Nudge when the agent edits help-dialog.tsx OR use-review-keybindings.ts.
#
# These two files duplicate keyboard-shortcut definitions with no shared constant.
# Editing one without the other produces UI/handler drift. This hook prints a
# reminder; it never blocks.
set +e

input=$(cat)

file=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("file_path", ""))
' 2>/dev/null)

case "$file" in
  *"/frontend/src/components/review/help-dialog.tsx"|*"/frontend/src/hooks/use-review-keybindings.ts")
    cat <<'EOF' >&2
⚠ Keyboard-shortcut surfaces are duplicated:
  - frontend/src/components/review/help-dialog.tsx (hardcoded MARK_ROWS + shortcut table — what users SEE)
  - frontend/src/hooks/use-review-keybindings.ts (the actual keyboard handler — source of truth)

If you changed shortcut behavior, edit the OTHER file too.
There is no shared constant — see frontend/CLAUDE.md and HUMAN_REVIEW_GUIDE.md.
EOF
    ;;
esac

exit 0
