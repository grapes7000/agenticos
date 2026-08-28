# Active Task

## BUILD-001A — Bootstrap Python package and CLI entry point

**Checkpoint:** 1 — Core framework + `agent status`

**Status:** TODO

## Outcome

Create the minimal Python packaging/CLI skeleton required for later AgenticOS checks. At the end of this slice, an editable install in a virtual environment should expose an `agent` command that can display help/version and exit cleanly.

## Scope

Expected files:

- `pyproject.toml`
- `agenticos/__init__.py`
- `agenticos/cli.py`

Do not implement checks, Rich status rendering, subprocess helpers, Tailscale, disk, networking, or future architecture in this task.

## Acceptance criteria

- project installs in a venv/editable mode;
- `agent --help` works;
- a simple version command/flag works if included in the chosen minimal CLI design;
- package imports without side effects;
- no diagnostic logic yet;
- implementation is small enough to understand completely before BUILD-001B.

## Development method

Ask ChatGPT for a **self-contained Qwen prompt for BUILD-001A**. Give that prompt to Qwen without repository files. Paste only the requested output into the exact paths, run the proof commands from the prompt, and commit the slice when it passes.
