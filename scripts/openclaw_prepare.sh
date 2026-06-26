#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/AgenticOS"
SANDBOX="${AGENTOS_OPENCLAW_SANDBOX:-$HOME/AgenticOS/openclaw-sandbox}"
mkdir -p "$SANDBOX/context" "$SANDBOX/output" "$SANDBOX/runbooks"
cat > "$SANDBOX/README.md" <<'MD'
# OpenClaw Sandbox for AgenticOS

This folder is the safe starting point for OpenClaw.

Use OpenClaw here first, not across the entire desktop.

## Hard rules

- Do not grant wallet, bank, browser-cookie, password-manager, SSH-key, or seed-phrase access.
- Do not allow automatic file deletion or moving.
- Do not route OpenClaw directly into your full home folder.
- Start with the generated context pack: `context/agenticos-context.md`.
- Have OpenClaw write proposed actions into `output/` before you run anything.

## Good first prompts

Ask OpenClaw:

> Read context/agenticos-context.md and summarize AgenticOS status. Do not change files.

> Read context/agenticos-context.md and propose the next three safe improvements. Write them to output/next-actions.md.

> Create a dry-run plan for improving AgenticOS memory search. Do not run commands.
MD

cat > "$SANDBOX/.env.template" <<'ENV'
# OpenClaw provider keys go here if you use cloud models.
# Keep this file out of Obsidian and Git.
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# OPENROUTER_API_KEY=
# OPENCLAW_DATA_DIR=$HOME/.openclaw
ENV

bash scripts/openclaw_context_pack.sh

echo "OpenClaw sandbox prepared at: $SANDBOX"
echo "OpenClaw install command, when you are ready:"
echo "  curl -fsSL https://openclaw.ai/install.sh | bash"
echo "Then run onboarding:"
echo "  openclaw onboard --install-daemon"
