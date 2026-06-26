#!/usr/bin/env bash
set -euo pipefail

VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"
TODAY="$(date +%F)"

echo "# AgenticOS Context - $TODAY"
echo ""

echo "## System"
echo "- User: $USER"
echo "- Host: $(hostname)"
echo "- Date: $TODAY"
echo "- AgenticOS path: $HOME/AgenticOS"
echo "- Vault path: $VAULT"
echo ""

echo "## AgenticOS Files"
echo '```'
find "$HOME/AgenticOS" -maxdepth 3 -type f | sort | sed "s|$HOME|~|"
echo '```'
echo ""

echo "## Database"
if [ -f "$HOME/AgenticOS/data/db/agent_os.sqlite" ]; then
  echo "- Database exists ✅"
  echo "- Size: $(du -h "$HOME/AgenticOS/data/db/agent_os.sqlite" | awk '{print $1}')"
else
  echo "- Database missing ❌"
fi
echo ""

echo "## Latest File Butler Note"
LATEST_FILE_PLAN="$(find "$VAULT/Agentic OS/File Plans" -type f -name "*.md" 2>/dev/null | sort | tail -n 1 || true)"
if [ -n "$LATEST_FILE_PLAN" ]; then
  echo "- File: $LATEST_FILE_PLAN"
  echo ""
  echo '```markdown'
  sed -n '1,160p' "$LATEST_FILE_PLAN"
  echo '```'
else
  echo "- No File Butler note found."
fi
echo ""

echo "## Latest Daily Briefing"
LATEST_BRIEFING="$(find "$VAULT/Agentic OS/Daily Briefings" -type f -name "*.md" 2>/dev/null | sort | tail -n 1 || true)"
if [ -n "$LATEST_BRIEFING" ]; then
  echo "- File: $LATEST_BRIEFING"
  echo ""
  echo '```markdown'
  sed -n '1,220p' "$LATEST_BRIEFING"
  echo '```'
else
  echo "- No Daily Briefing found."
fi
echo ""

echo "## Hermes Cron"
if command -v hermes >/dev/null 2>&1; then
  echo '```'
  hermes cron list 2>&1 || true
  echo '```'
else
  echo "- Hermes command not found."
fi
echo ""

echo "## Ollama"
if command -v ollama >/dev/null 2>&1; then
  echo '```'
  ollama list 2>&1 || true
  echo '```'
else
  echo "- Ollama command not found."
fi
