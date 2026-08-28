# Architecture

## Core rule

System logic lives in reusable Python modules. Interfaces consume structured results; they do not own Linux diagnostics.

```text
Linux / system commands
        ↓
   command runner
        ↓
      checks
        ↓
 structured results
        ↓
 ┌──────┼────────┬────────┐
 CLI    TUI      Qt      AI/automation
```

Only the CLI is implemented first.

## Initial package layout

```text
agenticos/
├── __init__.py
├── models.py
├── runner.py
├── cli.py
└── checks/
    ├── __init__.py
    ├── network.py
    ├── system.py
    ├── docker.py
    └── ollama.py
```

Do not create future directories merely because the roadmap mentions them.

## Result model

Checkpoint 1 introduces a small `Status` enum and `CheckResult` dataclass. The contract should communicate whether something is healthy/degraded/broken plus a concise summary and optional explanation. Later checkpoints may extend this only when concrete use cases require it.

Checks return data. They do not print.

## Command runner

All external commands go through one runner wrapper around `subprocess.run`.

The runner should make command execution predictable by capturing stdout/stderr, preserving exit codes, applying a finite timeout, and representing expected execution failures such as missing binaries or timeouts without forcing every check to duplicate try/except logic.

The runner does not interpret domain meaning. For example, it knows `systemctl` exited 3; the Tailscale check decides what that means.

## Checks

A check answers a narrow read-only question and returns `CheckResult`.

Examples:

```text
check_tailscale()
check_internet()
check_root_disk()
check_failed_services()
check_mullvad_route()
check_docker_daemon()
check_ollama_service()
```

Checks may combine lower-level facts when a user-facing question requires interpretation, but the logic should remain testable.

## Checks vs actions

This is a hard safety boundary:

```text
check = inspect only
action = intentionally change state
```

No action layer is introduced in Checkpoints 1–5. Future restart/cleanup/install/fix operations must not be hidden inside checks.

## Domain grouping

- `network.py`: reachability, Tailscale, DNS, Mullvad, route-source facts.
- `system.py`: disk, memory, load, temperatures, uptime, systemd failures.
- `docker.py`: daemon and container/self-hosting health.
- `ollama.py`: local Ollama endpoint, models, running models, related service checks.
- later `dev.py`: Git, Python, Node, tests, project environment.
- later `homelab.py`: remote reachability, SSH, services, storage, backup freshness, routing safety.

## Rendering

Rich is the first renderer. It receives result objects and chooses presentation. A check must never embed Rich markup or terminal behavior.

Later TUI/Qt implementations call Python APIs directly. They must not execute `agent` and parse its human-readable terminal output.

## AI boundary

Local AI can eventually summarize or explain already-established results. It should not decide factual system state when deterministic checks can do so.

Example:

```text
Python facts: route missing + tailscaled active + Mullvad tunnel active
             ↓
Deterministic classification: DEGRADED
             ↓
Optional AI: explain the consequence conversationally
```

## Testing strategy

Mock the command runner at check boundaries. Tests should cover healthy, degraded, broken, command-missing, timeout, and malformed-output cases without depending on the machine running the test.
