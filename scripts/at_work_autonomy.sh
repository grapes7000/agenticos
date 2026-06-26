#!/usr/bin/env bash
set -euo pipefail

cd "${AGENTOS_HOME:-$HOME/AgenticOS}"

if [ -z "${OBSIDIAN_VAULT:-}" ]; then
  if [ -d "$HOME/Documents/Obsidian Vault" ]; then
    export OBSIDIAN_VAULT="$HOME/Documents/Obsidian Vault"
  else
    export OBSIDIAN_VAULT="$HOME/vault"
  fi
fi

export AGENTOS_HOME="${AGENTOS_HOME:-$HOME/AgenticOS}"
export AGENTOS_MODEL="${AGENTOS_MODEL:-qwen2.5-coder:7b}"

LOG_DIR="$OBSIDIAN_VAULT/Agentic OS/Run Logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(date +%F_%H-%M-%S) At Work Autonomy Run.log"

run_step() {
  local name="$1"
  shift
  {
    printf '\n===== %s =====\n' "$name"
    "$@"
  } 2>&1 | tee -a "$LOG"
}

printf 'AgenticOS at-work autonomy run started: %s\n' "$(date --iso-8601=seconds)" | tee -a "$LOG"
printf 'Vault: %s\n' "$OBSIDIAN_VAULT" | tee -a "$LOG"
printf 'Mode: read-only / dry-run reports only\n' | tee -a "$LOG"

run_step "Initialize database" python3 tools/init_db.py

IFS=':' read -r -a SCAN_DIRS <<< "${AGENTOS_FILE_SCAN_DIRS:-$HOME/Downloads:$HOME/Desktop:$HOME/Documents}"
for dir in "${SCAN_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    run_step "Scan files: $dir" python3 tools/scan_folder.py "$dir"
  else
    printf '\n===== Scan files: %s =====\nSkipped missing directory.\n' "$dir" | tee -a "$LOG"
  fi
done

# These agents only write Markdown/dry-run reports.
run_step "File Butler dry-run" python3 agents/file_butler.py
run_step "Health report" python3 agents/health_watchdog.py
run_step "Memory digest" python3 agents/memory_digest.py
run_step "Change report" python3 agents/changes_report.py
run_step "Static dashboard" python3 agents/dashboard.py

# Daily briefing uses public web sources; keep going if the network/API is down.
run_step "Daily briefing" python3 agents/daily_briefing.py || true

# Operator report uses local Ollama. If Ollama is unavailable, the script writes an error note instead.
run_step "Operator report" python3 agents/operator_report.py || true

run_step "Homecoming briefing" python3 agents/homecoming_report.py

printf '\nAgenticOS at-work autonomy run complete: %s\nLog: %s\n' "$(date --iso-8601=seconds)" "$LOG" | tee -a "$LOG"
