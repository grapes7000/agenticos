#!/usr/bin/env bash
set -euo pipefail
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"
"$HOME/AgenticOS/scripts/layer3_run.sh"
echo "AgenticOS Layer 3 complete. Check Obsidian > Agentic OS."
