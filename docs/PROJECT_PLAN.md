# Project Plan

## Phase A — Diagnostic CLI foundation

### Checkpoint 1
Core result model, command runner, baseline network/system checks, Rich `agent status`.

### Checkpoint 2
Network/VPN intelligence and `agent network`, including internet vs DNS state, Tailscale connectivity, public exit identity, Mullvad use, and local-vs-Tailscale Mullvad route source.

### Checkpoint 3
Complete local machine health through `agent system`: CPU/load, memory/swap, storage, uptime, thermal metrics when available, and failed services.

### Checkpoint 4
Read-only Docker/self-hosting diagnostics through `agent docker`.

### Checkpoint 5
Read-only Ollama/local-AI diagnostics through `agent ollama`.

## Phase B — Complete the CLI utility

### Checkpoint 6 — Development tools

`agent dev`: Git state, Python environment/venv, common Node tooling where relevant, project checks/doctor adapters, and understandable environment mistakes.

### Checkpoint 7 — Homelab tools

`agent homelab`: reachability, Tailscale/SSH, remote service/container health, storage, backup freshness, and homelab-specific Mullvad/tailnet routing safety.

### Checkpoint 8 — Explicit actions

Introduce `ActionResult` and a state-changing layer separate from checks. Begin only with bounded, understandable actions such as restarting a chosen service/container or creating a development venv. Add confirmation/dry-run semantics where appropriate.

### Checkpoint 9 — Guided troubleshooting

Combine related check results into deterministic explanations and recommended actions. Optionally allow Ollama to rewrite established facts into more conversational explanations, without giving the model authority over system truth.

### Checkpoint 10 — Configuration and machine-readable interfaces

Machine roles, thresholds, host/endpoints, optional checks, `--verbose`, `--json`, stable exit codes, and shell completion.

### Checkpoint 11 — CLI v1.0

Packaging/install flow, public Python API cleanup, full regression tests, documentation, command consistency, failure handling, and a release checklist.

## Phase C — Visual interfaces

### TUI

Build an interactive terminal dashboard using the same backend. Good for SSH/homelab/development use. Drill into checks, evidence, explanations, and available actions.

### PySide6/Qt GUI

Build a workstation control-center interface using the same backend. It should present overview, system, network, containers, AI, development, homelab, and actions without reimplementing diagnostics.

The project may ship either or both interfaces depending on daily usefulness.

## Phase D — Daily-use discovery

Use AgenticOS normally. Whenever a recurring raw Linux command or multi-command recipe appears, ask:

> Is this a reusable check or action?

If yes:

1. add/test the backend capability;
2. expose it in the CLI;
3. use it long enough to validate the UX;
4. surface it in TUI/Qt where useful.

This phase is intentionally open-ended and is how AgenticOS becomes a durable personal Linux knowledge layer rather than a fixed one-off dashboard.
