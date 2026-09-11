# AI Rules for AgenticOS

These rules apply when ChatGPT, Qwen, Ollama chat, Claude chat, or another AI helps with this repository.

## Authority order

1. Latest explicit user instruction.
2. `docs/ACTIVE_TASK.md`.
3. `TASKS.md` checkpoint/task contract.
4. This file.
5. `docs/03_ARCHITECTURE.md` and `docs/DECISIONS.md`.
6. Existing code patterns.

## Development model

AgenticOS deliberately uses two AI roles:

- **Qwen/local chat model:** writes one very small implementation slice from a self-contained prompt.
- **ChatGPT:** defines the detailed prompt when requested, then reviews and explains the completed checkpoint after all lettered tasks are implemented and tested.

The human controls files, terminal commands, tests, Git, checkpoint advancement, and acceptance.

## One-slice rule for Qwen

Implement exactly the requested lettered BUILD task or smaller sub-slice. Do not automatically continue to the next task.

For Checkpoints 1–5, the prompt should contain enough technical context that Qwen does **not** need uploaded repository files/documents for proof-of-working-code tasks. If compatibility with existing code is required, provide the exact public interface or the smallest relevant code excerpt in the prompt rather than asking Qwen to inspect the whole repository.

## Qwen delivery format

For each requested slice, return:

1. exact repository path;
2. `NEW FILE`, `COMPLETE REPLACEMENT`, or tightly scoped `TARGETED EDIT`;
3. complete copy-pastable code for the requested file(s);
4. a short explanation;
5. exact focused test/proof commands;
6. no unrelated future implementation.

Never claim a command was run unless the AI actually has tool access and ran it or the user supplied the output.

## Architecture boundaries

- Checks are read-only.
- Checks return structured Python data and do not print.
- External commands go through the shared command runner once it exists.
- CLI/rendering code owns terminal presentation.
- Do not put Rich markup or UI behavior inside checks.
- Do not add `sudo`, package installs, service restarts, Docker mutation, route changes, deletion, cleanup, or other intentional state changes to Checkpoints 1–5.
- Do not add a generic plugin framework, daemon, TUI, Qt GUI, or AI orchestration unless the active task explicitly reaches that stage.
- Deterministic code owns factual health classification; an LLM may later explain those facts.

## Implementation rules

- Prefer the smallest correct implementation over abstraction for hypothetical future needs.
- Preserve established public interfaces from completed tasks.
- Add a dependency only when the checkpoint explicitly calls for it or the human approves it.
- Use finite timeouts for external commands/network calls.
- Prefer exit codes and machine-readable output over parsing human/decorative output.
- Normal environmental differences should return understandable states, not uncaught tracebacks.
- Do not create parallel files named `new`, `fixed`, `final`, `backup`, etc.
- Never expose or commit secrets.

## Testing

Unit tests should normally mock command execution and network requests so test results do not depend on whether Tailscale, Mullvad, Docker, Ollama, or Open WebUI happen to be active on the developer machine.

A task is not done just because its happy path runs once. Test the meaningful classifications and expected failure paths named in `TASKS.md`.

## Checkpoint review

When all lettered tasks in a checkpoint are complete, stop before beginning the next checkpoint. The checkpoint review should inspect:

- full diff against the checkpoint base;
- all test results;
- real smoke-test output for the checkpoint command;
- architecture fit;
- brittle parsing or environment assumptions;
- acceptance criteria;
- code the human should understand before accepting it.

After necessary fixes and passing checks, the human may merge and advance.

## Git safety

The human controls Git lifecycle. Do not assume permission to push, merge, force-push, reset, clean, delete branches, or rewrite history.

Recommended structure is one branch per checkpoint with small commits for each lettered task.

## Documentation updates

Update durable docs when state changes:

- `docs/CURRENT_STATE.md`
- `docs/AI_HANDOFF.md`
- `docs/DECISIONS.md` when a durable decision changes
- `docs/BUGS.md` for unresolved defects
- `docs/CHANGELOG.md` for user-visible completed capability
- `docs/ACTIVE_TASK.md` for the current lettered task

Do not turn documentation into a transcript.
