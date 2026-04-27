#!/usr/bin/env bash
# H4: Nudge when the agent edits a backend API or store file.
#
# Pydantic models in src/web/api/*.py and src/web/*_store.py are mirrored by
# hand into frontend/src/types/. Any shape change there needs a corresponding
# update on the frontend. This hook prints a reminder; it never blocks.
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
  *"/src/web/api/"*.py|*"/src/web/"*"_store.py")
    cat <<EOF >&2
⚠ Backend edit at: $file

If response shapes or request bodies changed, mirror in:
  - frontend/src/types/<domain>.ts   (hand-maintained, 1:1 with Pydantic)
  - frontend/src/api/<domain>.ts     (typed fetch client)
  - frontend/src/hooks/use-<domain>.ts  (only if return shape changed)

Recipe: .claude/skills/sync-types-with-backend/SKILL.md
Then: cd frontend && npm run build  (catches most drift via tsc -b)
EOF
    ;;
esac

exit 0
