# Hermes Scheduling Notes for Agentic OS Layer 1

After Hermes is installed and configured, use it to schedule these scripts.

## Script-only jobs, zero LLM spend
These can run without calling a model:

```bash
agentos file-scan
agentos memory
```

## LLM-driven jobs
These may call your local Ollama model:

```bash
agentos briefing
agentos research <URL>
```

## Suggested schedules
- Daily briefing: 9:00 AM
- File Butler dry run: 8:00 PM
- Memory note: after file scan, or nightly

Keep Layer 1 safe: all file organization remains dry-run until reviewed.
