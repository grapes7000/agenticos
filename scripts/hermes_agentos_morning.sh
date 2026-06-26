#!/usr/bin/env bash
set -euo pipefail
export AGENTOS_HOME="${AGENTOS_HOME:-$HOME/AgenticOS}"
export OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"
"$AGENTOS_HOME/scripts/morning_run.sh"
echo "AgenticOS Hermes wrapper finished."
