#!/usr/bin/env bash
set -u

fail=0
warn=0

ok()   { printf '✅ %s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*"; warn=$((warn+1)); }
bad()  { printf '❌ %s\n' "$*"; fail=$((fail+1)); }

printf 'VibeLab project preflight\n\n'

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "Git repository detected"
else
  bad "Not inside a Git repository"
fi

for file in README.md AGENTS.md docs/PROJECT_PLAN.md docs/AI_HANDOFF.md docs/DECISIONS.md docs/BUGS.md docs/TESTING.md; do
  if [[ -f "$file" ]]; then
    ok "$file present"
  else
    bad "$file missing"
  fi
done

if git diff --check >/dev/null 2>&1; then
  ok "git diff --check passed"
else
  bad "git diff --check found whitespace errors"
fi

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  warn "Working tree has uncommitted changes"
else
  ok "Working tree is clean"
fi

if git ls-files | grep -Eq '(^|/)(\.env($|\.)|.*\.(pem|key)$)'; then
  bad "Potential secret-bearing file is tracked by Git"
else
  ok "No obvious .env/.pem/.key files tracked"
fi

printf '\nSummary: %d failure(s), %d warning(s)\n' "$fail" "$warn"
[[ "$fail" -eq 0 ]]
