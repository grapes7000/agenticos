#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AgenticOS"
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"
python3 tools/ensure_layer3_schema.py
python3 tools/index_obsidian_memory.py || true
python3 agents/health_watchdog.py
python3 agents/evaluator.py
python3 agents/project_guardian.py
python3 agents/handoff_writer.py
bash scripts/openclaw_context_pack.sh
printf '\nLayer 3 run complete. Check Obsidian > Agentic OS.\n'
