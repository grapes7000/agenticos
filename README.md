# AgenticOS

AgenticOS is a personal Linux control layer that turns accumulated shell commands, diagnostic recipes, and multi-command workflows into named Python **checks** and **actions** with clear human explanations.

The goal is not to replace Linux or hide it. The goal is to make the parts of Linux I repeatedly use easier to inspect, understand, and operate.

Instead of remembering commands such as `systemctl`, `ip rule`, `docker inspect`, `tailscale status`, `df`, or project-specific doctor commands, AgenticOS will expose stable commands such as:

```bash
agent status
agent network
agent system
agent docker
agent ollama
agent dev
agent homelab
```

The CLI is the first complete product. Later, the same Python backend may power a terminal UI, a PySide6/Qt GUI, local-AI tools, and lightweight background health monitoring.

## Core design

- **Checks are read-only.** They inspect the computer and return structured facts.
- **Actions are separate.** Any operation that changes state is explicit and introduced later.
- **Linux facts are deterministic.** Python decides whether a service, route, container, disk, or endpoint is healthy.
- **Human explanations are first-class.** Results should say what happened, why it matters, and what to inspect next.
- **UI code never owns system logic.** CLI/TUI/GUI/AI layers consume the same Python result objects.
- **Small slices over giant AI rewrites.** Local chat models write narrowly scoped pieces that can be pasted, run, and understood.

## Development workflow

This repository is human-operated. Qwen or another local chat model writes one small slice from a self-contained prompt. The human pastes it into the named file and runs the specified checks. A full checkpoint is completed before ChatGPT reviews the combined code, catches design problems, and explains how the implementation works.

The first five checkpoints are planned in [`TASKS.md`](TASKS.md):

1. Core result model, command runner, four baseline checks, and `agent status`.
2. Network/VPN intelligence, including Mullvad route-source detection.
3. Complete local system-health diagnostics.
4. Docker and self-hosting diagnostics.
5. Ollama/local-AI diagnostics.

After those, the CLI continues through development tools, homelab tools, explicit actions, guided troubleshooting, configuration, machine-readable output, packaging, and CLI v1.0. TUI/Qt work begins only after the CLI backend is complete enough to be the source of truth.

## Start here

Read [`START_HERE.md`](START_HERE.md), then begin with `BUILD-001A` in [`TASKS.md`](TASKS.md).

## Planned package shape

The exact structure may evolve, but the intended direction is intentionally small:

```text
agenticos/
├── models.py
├── runner.py
├── cli.py
└── checks/
    ├── network.py
    ├── system.py
    ├── docker.py
    └── ollama.py
```

Later additions such as `actions/`, TUI, Qt, configuration, and AI integration should be added only when their checkpoint requires them.

## Safety boundary

A function under `checks/` may inspect state but must not intentionally modify the machine. Restarting services, deleting data, changing routes, installing packages, cleaning caches, or otherwise mutating state belongs to a future explicit action layer with appropriate confirmation and safety rules.
