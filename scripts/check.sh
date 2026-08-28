#!/usr/bin/env bash
set -u

failures=0
ran=0

run_check() {
  local label="$1"
  shift
  echo
  echo "==> $label"
  ran=$((ran + 1))
  if "$@"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    failures=$((failures + 1))
  fi
}

if [[ -x ./scripts/preflight.sh ]]; then
  run_check "repository preflight" ./scripts/preflight.sh
else
  run_check "repository preflight" bash ./scripts/preflight.sh
fi

if [[ -f pyproject.toml || -f pytest.ini || -d tests ]]; then
  if command -v pytest >/dev/null 2>&1; then
    run_check "pytest" pytest
  else
    echo "WARN: Python tests appear configured but pytest is not installed/in PATH."
  fi
fi

if [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
  if npm run | grep -qE '^  lint($|:)'; then
    run_check "npm lint" npm run lint
  fi
  if npm run | grep -qE '^  typecheck($|:)'; then
    run_check "npm typecheck" npm run typecheck
  fi
  if npm run | grep -qE '^  test($|:)'; then
    run_check "npm test" npm test -- --runInBand
  fi
  if npm run | grep -qE '^  build($|:)'; then
    run_check "npm build" npm run build
  fi
fi

if [[ -f Cargo.toml ]] && command -v cargo >/dev/null 2>&1; then
  run_check "cargo test" cargo test
fi

if [[ -f go.mod ]] && command -v go >/dev/null 2>&1; then
  run_check "go test" go test ./...
fi

echo
if (( ran == 1 )); then
  echo "NOTE: Only the generic preflight was detected. Add project-specific verification commands to docs/TESTING.md and docs/ACTIVE_TASK.md."
fi

echo "Checks run: $ran | Failures: $failures"

if (( failures > 0 )); then
  exit 1
fi
