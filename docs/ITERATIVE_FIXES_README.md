# AgenticOS Iterative Fixes Layer

This layer adds a safe test-and-fix loop to AgenticOS.

## New commands

```bash
agentos test
agentos bug-hunt
agentos fix-cycle
agentos fix-status
```

Fallback direct commands:

```bash
~/AgenticOS/bin/agentos-test
~/AgenticOS/bin/agentos-bug-hunt
~/AgenticOS/bin/agentos-fix-cycle
~/AgenticOS/bin/agentos-fix-status
```

## What each command does

### `agentos test`
Runs a system test suite and writes a Markdown report into Obsidian:

```text
Agentic OS/Test Reports/
```

### `agentos bug-hunt`
Collects system context, latest test report, and AgenticOS source snippets. Then it asks local Ollama/Qwen to look for bugs and risky weak spots. It writes a Markdown bug report into:

```text
Agentic OS/Bug Reports/
```

If Ollama is not running, it still writes a fallback report with static checks.

### `agentos fix-cycle`
Runs tests, runs the bug hunter, and creates a patch plan. It does **not** apply patches automatically. The output goes to:

```text
Agentic OS/Fix Cycles/
Agentic OS/Patch Plans/
```

## Safety rules

This layer is intentionally conservative:

- No automatic deletion.
- No automatic moving or renaming of user files.
- No wallet/bank/credential access.
- No automatic patch application.
- No `sudo`.
- No editing outside `~/AgenticOS` unless you explicitly do it yourself.

The goal is to make the AI find bugs and propose fixes, while you stay in control.
