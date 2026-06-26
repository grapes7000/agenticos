# AgenticOS Layer 3 + OpenClaw Prep

This upgrade adds:

- Obsidian memory indexing into SQLite chunks
- optional Ollama embeddings with `nomic-embed-text`
- `agentos search "query"`
- health watchdog
- evaluator/guard report
- project guardian
- formal handoff files
- OpenClaw sandbox/context pack
- Qwen/GStack-style commands and skills

## Start

```bash
source ~/.bashrc
agentos layer3
agentos search "Hermes cron"
agentos openclaw-prep
```

## OpenClaw safety model

OpenClaw should begin with this generated context file:

```text
~/AgenticOS/openclaw-sandbox/context/agenticos-context.md
```

Do not start OpenClaw with full home-folder or secret access.
