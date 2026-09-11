# Testing

## Principle

AgenticOS should be testable without depending on the machine running the test. Most check tests therefore mock the shared command runner and feed deterministic stdout/stderr/exit-code fixtures into parsing/classification logic.

## Required coverage pattern

For each check, add focused tests for the states that matter to the user:

- healthy/normal;
- degraded/warning;
- broken/unavailable;
- required command missing;
- timeout or command failure where relevant;
- malformed/unexpected output where parsing exists.

Not every check needs every case, but every meaningful classification branch should be exercised.

## Runner tests

The command runner itself should cover:

- successful command;
- nonzero exit status;
- missing executable;
- timeout;
- permission failure if represented explicitly.

## What not to do

- Do not require Tailscale, Mullvad, Docker, Ollama, or Open WebUI to be installed for the unit suite.
- Do not hit public APIs in unit tests.
- Do not mutate system state to create test conditions.
- Do not disable tests because the local machine has a different configuration.

## Real-machine checkpoint proof

Mocks prove logic. Each checkpoint also needs one manual smoke test on the actual machine:

```text
Checkpoint 1: agent status
Checkpoint 2: agent network
Checkpoint 3: agent system
Checkpoint 4: agent docker
Checkpoint 5: agent ollama
```

The manual run should never be the only proof of correctness.

## Default test command

Once pytest is introduced:

```bash
python -m pytest -q
```

Each self-contained Qwen prompt should also include the smallest focused test command for the slice it implements.
