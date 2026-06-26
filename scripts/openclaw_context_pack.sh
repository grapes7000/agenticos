#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AgenticOS"
VAULT="${OBSIDIAN_VAULT:-$HOME/vault}"
SANDBOX="${AGENTOS_OPENCLAW_SANDBOX:-$HOME/AgenticOS/openclaw-sandbox}"
mkdir -p "$SANDBOX/context" "$VAULT/Agentic OS/OpenClaw"
OUT="$SANDBOX/context/agenticos-context.md"
{
  echo "# AgenticOS Context Pack for OpenClaw"
  echo ""
  echo "Generated: $(date -Iseconds)"
  echo ""
  echo "## Rules"
  echo "- Read this context pack only."
  echo "- Do not read wallets, seed phrases, browser cookies, private SSH keys, bank files, or password files."
  echo "- Do not delete, move, rename, overwrite, trade, email, message, or spend money without explicit approval."
  echo "- For file actions, write a dry-run plan first."
  echo ""
  for folder in "Health" "Evaluations" "Handoffs" "Operator Reports" "Daily Briefings" "File Plans" "Change Reports"; do
    latest=$(find "$VAULT/Agentic OS/$folder" -type f -name '*.md' 2>/dev/null | sort | tail -n 1 || true)
    if [ -n "$latest" ]; then
      echo "## Latest $folder"
      echo "Source: $latest"
      echo '```markdown'
      sed -n '1,220p' "$latest"
      echo '```'
      echo ""
    fi
  done
} > "$OUT"
cp "$OUT" "$VAULT/Agentic OS/OpenClaw/agenticos-context.md"
echo "Wrote OpenClaw context pack: $OUT"
echo "Copied to: $VAULT/Agentic OS/OpenClaw/agenticos-context.md"
