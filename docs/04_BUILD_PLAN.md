# Build Plan

AgenticOS is built in checkpoints. A checkpoint is the review boundary: finish all lettered tasks, run the checkpoint verification, then bring the completed checkpoint to ChatGPT for code review and explanation before starting the next checkpoint.

Within a checkpoint, each lettered task is intentionally small enough for a local chat model such as Qwen to implement from a self-contained prompt.

## Checkpoint 1 — Core framework and `agent status`

Goal: prove the core architecture with four read-only checks and one polished CLI command.

Deliverables:

- package/bootstrap and installable `agent` command;
- `Status` + `CheckResult` result model;
- reusable subprocess runner;
- Tailscale and internet checks;
- root-disk and failed-systemd-unit checks;
- Rich status renderer;
- focused tests using mocks.

User-visible proof:

```bash
agent status
```

## Checkpoint 2 — Network and VPN intelligence

Goal: replace common network/VPN diagnostic recipes with one understandable command.

Deliverables:

- `agent network`;
- Tailscale details beyond a simple service check;
- DNS reachability/resolution check;
- public exit identity/IP lookup with bounded network timeout;
- Mullvad detection;
- distinguish local Mullvad VPN/tunnel from Tailscale-provided Mullvad exit routing when evidence supports the distinction;
- route sanity and useful human explanations for ambiguous/degraded states;
- tests for each routing state.

User-visible proof:

```bash
agent network
```

should answer: Am I online? Is Tailscale working? Am I exiting through Mullvad? If yes, by which path?

## Checkpoint 3 — System health

Goal: make `agent system` a useful local-machine health summary.

Deliverables include memory/swap, CPU/load, filesystem usage, uptime, temperatures when available, failed services, and sane severity thresholds. Optional hardware metrics must degrade gracefully when the required source/tool does not exist.

## Checkpoint 4 — Docker and self-hosting diagnostics

Goal: explain Docker health without requiring routine `docker ps`, `inspect`, and disk-usage interpretation.

Deliverables include daemon availability, running/stopped/unhealthy containers, restart loops/restart counts where available, port summary, Docker disk usage, Compose/project context when practical, and readable explanations. Still read-only.

## Checkpoint 5 — Ollama and local-AI diagnostics

Goal: understand the local Ollama stack through `agent ollama`.

Deliverables include endpoint/service health, installed models, running/loaded models, useful resource/context information where reliably detectable, and optional Open WebUI endpoint connectivity. The deterministic Python layer owns status; no LLM-generated diagnosis is required yet.

## After Checkpoint 5 — route to CLI v1.0

The next planned domains are:

6. development environment (`agent dev`);
7. homelab diagnostics (`agent homelab`);
8. explicit safe action model and first actions;
9. guided deterministic troubleshooting plus optional Ollama explanations;
10. configuration, machine roles, thresholds, verbose/JSON output, shell completion;
11. packaging, public Python API cleanup, documentation, test hardening, and CLI v1.0.

Only after the CLI/backend reaches that point should the project build a full TUI and/or PySide6/Qt GUI. Daily use then becomes the discovery mechanism for uncaught checks/actions: add them to the backend/CLI first, then expose them in each UI.

See `TASKS.md` for the lettered implementation slices for Checkpoints 1–5.
