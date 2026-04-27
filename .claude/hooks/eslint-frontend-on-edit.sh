#!/usr/bin/env bash
# H2: Advisory ESLint on edited frontend file (PostToolUse on Edit/Write/MultiEdit).
#
# Reads the tool invocation JSON from stdin, extracts tool_input.file_path, and
# runs eslint on JUST that file if it lives under frontend/src/.
#
# Output is informational — the hook never blocks. Failures are printed to stderr
# so the agent sees them in tool_use_output but the write itself succeeds.
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

# Only run for frontend TS/TSX files
case "$file" in
  *"/frontend/src/"*.tsx|*"/frontend/src/"*.ts) ;;
  *) exit 0 ;;
esac

# Resolve project root
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$root" ] && exit 0

# Need node_modules to run eslint
[ -x "$root/frontend/node_modules/.bin/eslint" ] || exit 0

# Run eslint on the single file, no color, max 30 lines of output
output=$(cd "$root/frontend" && ./node_modules/.bin/eslint --no-color "$file" 2>&1)
status=$?

if [ $status -ne 0 ]; then
  printf '⚠ ESLint advisory for %s:\n' "$file" >&2
  printf '%s\n' "$output" | head -30 >&2
fi

exit 0
