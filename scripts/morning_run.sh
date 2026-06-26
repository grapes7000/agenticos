#!/usr/bin/env bash
set -euo pipefail
cd "${AGENTOS_HOME:-$HOME/AgenticOS}"
if [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"

python3 tools/init_db.py
python3 tools/scan_folder.py "$HOME/Downloads"
if [[ -d "$HOME/Desktop" ]]; then python3 tools/scan_folder.py "$HOME/Desktop"; fi
python3 agents/file_butler.py
python3 agents/daily_briefing.py
python3 agents/memory_digest.py
python3 agents/dashboard.py
python3 agents/operator_report.py

echo "Morning run complete. Check: $OBSIDIAN_VAULT/Agentic OS"
