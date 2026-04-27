#!/usr/bin/env bash
# H3: Nudge when a NEW page file is written under frontend/src/pages/.
#
# AppShell's NAV_ITEMS array has no auto-discovery — adding a page file without
# wiring App.tsx + NAV_ITEMS leaves the route reachable but invisible in the
# sidebar. This hook fires on Write only (not Edit) so it doesn't spam on every
# edit to an existing page.
set +e

input=$(cat)

# Parse both file_path AND tool name from the input
parsed=$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_name", ""))
print(d.get("tool_input", {}).get("file_path", ""))
' 2>/dev/null)

tool=$(printf '%s' "$parsed" | sed -n '1p')
file=$(printf '%s' "$parsed" | sed -n '2p')

# Only fire on Write (new file creation), not Edit
[ "$tool" = "Write" ] || exit 0

# Only for new pages under frontend/src/pages/
case "$file" in
  *"/frontend/src/pages/"*.tsx) ;;
  *) exit 0 ;;
esac

# Skip well-known shared subpaths inside pages/ (e.g. */components/, */lib/)
case "$file" in
  *"/components/"*|*"/lib/"*|*"/utils/"*) exit 0 ;;
esac

cat <<EOF >&2
⚠ New page file detected: $file

A new page needs THREE places wired up — only the page file is obvious:
  1. frontend/src/App.tsx                           — add a lazy(...) import + route entry
  2. frontend/src/components/layout/app-shell.tsx   — add a NAV_ITEMS entry (no auto-discovery!)
  3. (optional) wire useBlocker() if the page has unsaved-changes editing

Recipe: .claude/skills/add-frontend-page/SKILL.md
EOF

exit 0
