#!/usr/bin/env bash
set -euo pipefail
cd "${AGENTOS_HOME:-$HOME/AgenticOS}"
if [[ -f .env ]]; then set -a; source .env; set +a; fi
python3 tools/init_db.py
python3 tools/doctor.py
python3 tools/scan_folder.py "$HOME/Downloads"
python3 agents/file_butler.py
python3 agents/lessons_agent.py add "Next layer installed" "The AgenticOS next-layer installer completed and the basic commands are available." --source installer
python3 agents/memory_digest.py
python3 agents/dashboard.py
