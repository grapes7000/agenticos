# AI Handoff

## Project

AgenticOS is a Python Linux control utility that turns recurring shell diagnostics/workflows into named read-only checks and later explicit actions, with human-readable output through one `agent` CLI.

## Current state

Planning is complete through Checkpoint 5. No implementation code has been written yet. The active task is `BUILD-001A`.

## Architecture that must be preserved

- shared `Status` + `CheckResult` model;
- shared subprocess runner;
- checks return data and do not print;
- checks are read-only;
- Rich CLI renders results;
- actions come later and are explicitly separate;
- deterministic code decides system facts/status;
- future TUI/Qt/AI interfaces consume the same Python backend rather than parsing CLI text.

## Development workflow

The developer wants local Qwen to write small proof-of-working-code slices. For the first five checkpoints, prompts should be self-contained enough that Qwen does not need uploaded repo files or planning docs. The developer will finish all lettered tasks in one checkpoint before asking ChatGPT for a combined review and plain-language code explanation.

When asked for a Qwen prompt, include exact files, interfaces, constraints, tests, delivery format, and explicit non-goals. Do not give Qwen the whole future roadmap unless needed.

## Current checkpoint

Checkpoint 1: package/CLI bootstrap, result model, command runner, two network checks, two system checks, Rich `agent status`, and tests.

## Important future requirement

Checkpoint 2 network diagnostics must determine whether traffic is actually using Mullvad and distinguish local Mullvad VPN/tunnel routing from a Tailscale-provided Mullvad exit path when evidence supports that distinction.

## Source of truth

- `TASKS.md` — task decomposition.
- `docs/03_ARCHITECTURE.md` — architecture.
- `docs/DECISIONS.md` — durable decisions.
- `docs/ACTIVE_TASK.md` — current slice.
- `docs/CURRENT_STATE.md` — current milestone/state.
