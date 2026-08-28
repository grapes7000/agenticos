# AgenticOS Tasks

Finish every lettered task in a checkpoint before asking ChatGPT to review that checkpoint. Each Qwen prompt should be self-contained and name the exact file(s), required interfaces, behavior, and test command. Do not ask Qwen to redesign the checkpoint.

Status values: `TODO`, `ACTIVE`, `DONE`, `BLOCKED`.

---

# Checkpoint 1 — Core framework + `agent status`

## BUILD-001A — Bootstrap Python package and CLI entry point — TODO

**Outcome:** minimal installable Python project with an `agent` command that can display help/version without diagnostics yet.

**Likely files:** `pyproject.toml`, `agenticos/__init__.py`, `agenticos/cli.py`.

**Acceptance:** install in a venv/editable mode; `agent --help` exits cleanly; no system checks implemented yet.

## BUILD-001B — Structured result model — TODO

**Outcome:** define a small `Status` enum and `CheckResult` dataclass used by all checks.

**Likely file:** `agenticos/models.py`.

**Required idea:** at least HEALTHY, DEGRADED, BROKEN; result has a name, status, summary, and optional human explanation/detail. Keep it intentionally small.

**Acceptance:** focused unit tests can construct each status; no printing or subprocess logic in this module.

## BUILD-001C — Safe command runner — TODO

**Outcome:** one reusable wrapper around `subprocess.run` so checks do not duplicate process/error handling.

**Likely file:** `agenticos/runner.py` plus tests.

**Required behavior:** argv-list input, captured stdout/stderr, preserved return code, finite timeout, understandable representation of missing command/timeout/permission failures. Runner does not classify domain health.

**Acceptance:** mocked tests cover success, nonzero exit, missing command, and timeout.

## BUILD-001D — Baseline network checks — TODO

**Outcome:** implement `check_tailscale()` and `check_internet()` returning `CheckResult` objects.

**Likely file:** `agenticos/checks/network.py` plus tests.

**Required behavior:** Tailscale checks actual service/availability; internet reachability uses a bounded probe and process exit status rather than searching English output such as `0% packet loss`.

**Acceptance:** healthy and unavailable paths tested; checks never print or modify state.

## BUILD-001E — Baseline system checks — TODO

**Outcome:** implement `check_root_disk()` and `check_failed_services()`.

**Likely file:** `agenticos/checks/system.py` plus tests.

**Required behavior:** disk health uses percentage thresholds with normal/warning/critical classification; failed systemd units are summarized without dumping raw output by default.

**Acceptance:** tests cover healthy/degraded/broken values and malformed/failed command output.

## BUILD-001F — `agent status` Rich renderer — TODO

**Outcome:** wire the four checks into one polished command.

**Likely file:** `agenticos/cli.py`, optionally a tiny rendering helper if justified.

**Required behavior:** compact table/panel, symbol + status + summary, more explanation for non-healthy results, overall status determined from the worst result, nonzero exit code when degraded/broken.

**Checkpoint proof:** `agent status` works on the real machine; test suite passes; output is understandable without reading Linux command output.

---

# Checkpoint 2 — Network + VPN intelligence

## BUILD-002A — Network detail/result support — TODO

**Outcome:** add only the minimal result metadata needed by richer network checks, if Checkpoint 1 proves it necessary.

**Constraint:** do not redesign `CheckResult`; add concrete fields only for demonstrated use such as metadata/evidence.

## BUILD-002B — Tailscale connection details — TODO

**Outcome:** determine whether Tailscale is merely installed/running versus actually connected, and expose useful connection facts.

**Likely file:** `agenticos/checks/network.py` plus tests.

**Acceptance:** distinguishes unavailable, service-down, disconnected, and connected states using stable/machine-readable output where available.

## BUILD-002C — DNS check — TODO

**Outcome:** tell the user whether name resolution works separately from raw internet reachability.

**Acceptance:** DNS failure can be shown even when an IP connectivity probe succeeds; bounded timeout; mocked tests.

## BUILD-002D — Public exit identity probe — TODO

**Outcome:** retrieve the current public exit IP and enough provider/identity information to help determine whether traffic is exiting through Mullvad.

**Constraint:** bounded timeout, graceful offline/API failure, no status should depend on one fragile prose string when a stronger signal exists.

## BUILD-002E — Mullvad route-source detection — TODO

**Outcome:** answer the user-facing question: **Is traffic using Mullvad, and is the path local Mullvad VPN/tunnel or a Tailscale-provided Mullvad exit route?**

**Implementation concept:** combine multiple deterministic signals such as Tailscale exit-node state, local Mullvad/WireGuard interface or service state, routes, and public-exit identity. Do not infer route source from one weak signal alone.

**Required classifications:** not using Mullvad; local Mullvad path; Tailscale Mullvad exit path; Mullvad detected but source ambiguous; inconsistent/degraded routing.

**Acceptance:** each classification has mocked tests and a human explanation.

## BUILD-002F — Route sanity checks — TODO

**Outcome:** catch obvious cases where VPN/Tailscale components are running but routing state is inconsistent.

**Scope:** read-only inspection only. Keep homelab-specific bypass-policy enforcement for the later homelab checkpoint unless a generic route check naturally applies.

## BUILD-002G — `agent network` command — TODO

**Outcome:** render internet, DNS, Tailscale, Mullvad, exit source/IP, and routing health in one coherent view.

**Checkpoint proof:** one command answers: online? DNS okay? Tailscale connected? Mullvad active? local tunnel or Tailscale exit path? any obvious routing issue?

---

# Checkpoint 3 — Local system health

## BUILD-003A — Memory and swap checks — TODO

**Outcome:** report memory/swap usage with sensible severity and clear units.

**Acceptance:** parsing logic isolated/tested; no alarming status simply because swap exists.

## BUILD-003B — CPU load/pressure check — TODO

**Outcome:** summarize load relative to CPU capacity rather than showing a context-free load number.

**Acceptance:** normal, sustained-high/degraded, and parse-failure tests.

## BUILD-003C — Filesystem inventory check — TODO

**Outcome:** expand beyond `/` to relevant mounted filesystems while ignoring pseudo/transient mounts that would create noise.

**Acceptance:** show only actionable local storage entries with thresholds.

## BUILD-003D — Uptime and boot context — TODO

**Outcome:** display uptime and useful boot/session facts without treating uptime itself as health failure.

## BUILD-003E — Temperature/thermal check — TODO

**Outcome:** report temperatures when reliable sensors are available; otherwise show unavailable/unsupported cleanly rather than BROKEN.

**Constraint:** optional hardware support must never crash the system view.

## BUILD-003F — Failed-services refinement — TODO

**Outcome:** improve Checkpoint 1 failed-unit reporting into useful service names/count/details while keeping healthy output compact.

## BUILD-003G — `agent system` command — TODO

**Outcome:** combine CPU/load, memory/swap, storage, thermal availability, uptime, and service failures into a readable system-health screen.

**Checkpoint proof:** `agent system` is useful on both a healthy desktop and a mocked degraded machine; all optional metrics fail gracefully.

---

# Checkpoint 4 — Docker + self-hosting diagnostics

## BUILD-004A — Docker daemon availability — TODO

**Outcome:** distinguish Docker command missing, daemon unavailable/permission denied, and daemon healthy.

## BUILD-004B — Container inventory and state parser — TODO

**Outcome:** obtain machine-readable container information and normalize it into Python structures.

**Required states:** running, stopped/exited, unhealthy/health-check failure where reported.

## BUILD-004C — Container health summaries — TODO

**Outcome:** convert inventory facts into concise `CheckResult` summaries; healthy fleets stay compact, failed containers are named.

## BUILD-004D — Restart-loop/restart-count signal — TODO

**Outcome:** identify suspicious repeated restarts when Docker exposes sufficient evidence.

**Constraint:** do not label one normal historical restart as a restart loop without a justified threshold/signal.

## BUILD-004E — Ports and service exposure summary — TODO

**Outcome:** present useful published-port facts without dumping raw Docker formatting.

## BUILD-004F — Docker storage usage — TODO

**Outcome:** summarize image/container/volume/build-cache disk usage from Docker's machine-readable or reliably parseable output.

## BUILD-004G — Compose/project context — TODO

**Outcome:** group or label containers by Compose project when labels/data make that reliable. Must degrade gracefully for standalone containers.

## BUILD-004H — `agent docker` command — TODO

**Outcome:** one view for daemon, containers, health problems, restarts, exposed ports, project grouping, and storage use.

**Checkpoint proof:** useful for everyday self-hosting diagnosis and entirely read-only.

---

# Checkpoint 5 — Ollama + local-AI diagnostics

## BUILD-005A — Ollama endpoint/service health — TODO

**Outcome:** determine whether the local Ollama API is reachable and distinguish command/service/endpoint failure modes where practical.

## BUILD-005B — Installed-model inventory — TODO

**Outcome:** query installed models through a stable API/structured interface and normalize name, size, and useful metadata.

## BUILD-005C — Running/loaded-model inventory — TODO

**Outcome:** identify models currently loaded/running and show available runtime metadata without guessing.

## BUILD-005D — Local AI resource context — TODO

**Outcome:** add modest, reliable context useful for running local models, such as available system memory and runtime-reported model memory where available.

**Constraint:** do not invent VRAM estimates or performance predictions from model name alone.

## BUILD-005E — Open WebUI connectivity — TODO

**Outcome:** optionally test a configured/default local Open WebUI endpoint and report reachable/not configured/unreachable cleanly.

**Constraint:** Open WebUI is supplemental; its absence must not make Ollama itself broken.

## BUILD-005F — `agent ollama` command — TODO

**Outcome:** render Ollama health, installed models, currently loaded models, resource context, and optional Open WebUI connectivity.

**Checkpoint proof:** `agent ollama` explains the local AI stack without invoking an LLM to diagnose itself.

---

# Later checkpoints — not yet decomposed

- Checkpoint 6: `agent dev`
- Checkpoint 7: `agent homelab`
- Checkpoint 8: explicit `ActionResult` model + first safe actions
- Checkpoint 9: guided troubleshooting + optional Ollama explanations
- Checkpoint 10: config, machine roles, thresholds, `--verbose`, `--json`, completion
- Checkpoint 11: packaging/API hardening/docs/tests → CLI v1.0
- Then: TUI and/or PySide6/Qt GUI on the same backend
