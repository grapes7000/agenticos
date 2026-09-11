# Requirements

## Functional requirements

1. Provide one installable `agent` CLI entry point.
2. Represent check outcomes with a shared structured result model rather than booleans or ad-hoc printed strings.
3. Support at least healthy, degraded, and broken states.
4. Centralize subprocess execution behind a reusable runner with timeout and useful error handling.
5. Keep check functions read-only and separate fact gathering from rendering.
6. Render concise human-readable CLI output with Rich.
7. Never require raw command output interpretation for the common healthy/degraded cases.
8. Add domain commands incrementally: status, network, system, docker, ollama, then dev and homelab.
9. Detect whether internet traffic is using Mullvad and distinguish a local Mullvad VPN/tunnel from a Tailscale-provided Mullvad exit path when evidence allows it.
10. Preserve enough structured detail that future TUI, Qt, JSON, automation, and AI layers can consume the same backend without scraping CLI text.

## Check-result requirements

A check result should eventually be able to express:

- stable machine-readable name/id;
- user-facing name;
- status/severity;
- short summary;
- optional explanation/detail;
- optional measured value or metadata;
- optional evidence useful for debugging;
- no side effects.

The exact dataclass should remain small in Checkpoint 1. Add fields only when later checkpoints prove they are needed.

## Reliability requirements

- Prefer command exit codes and machine-readable output over parsing decorative/English text when possible.
- Every subprocess call must have a finite timeout.
- Missing commands, permission errors, command failures, and malformed/unexpected output must produce understandable results instead of tracebacks during normal use.
- One failed check should not prevent unrelated checks from being displayed.
- Tests should mock command execution rather than depending on the developer machine's current network/service state.

## Safety requirements

- `checks/` is read-only by contract.
- No `sudo`, package installation, service restart, route mutation, file deletion, Docker deletion/cleanup, or other intentional state changes in the first five checkpoints.
- Future actions must live behind a separate explicit action API.
- Local AI may explain results later, but deterministic code owns health classification and factual system state.

## UX requirements

- Commands should be short and discoverable.
- Healthy summaries should be compact; degraded/broken results should provide more explanation.
- Raw output belongs behind optional detail/verbose behavior rather than being the default experience.
- A user should be able to understand why a status is degraded without knowing the underlying Linux command.

## Development requirements

- Each Qwen task should have one bounded outcome and normally touch one or two files.
- A self-contained prompt must be sufficient for Qwen to produce the requested slice; repository/file upload should not be required for proof-of-working-code tasks.
- Complete one checkpoint before ChatGPT performs the architecture/code review and explanation.
