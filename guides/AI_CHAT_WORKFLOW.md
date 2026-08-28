# AI Chat Workflow

The AI writes and explains. You operate the repository.

## What to send the AI

For implementation, start with the smallest useful context:

1. `docs/ACTIVE_TASK.md`
2. the directly relevant source files
3. only the architecture/decision sections needed for this task
4. exact error output, when debugging

Do not paste the entire repository by default. More context is not automatically better context.

## How generated code should be returned

Ask for each change as:

```text
PATH: app/example.py
ACTION: NEW FILE | COMPLETE REPLACEMENT | TARGETED EDIT

<code>

EXPLANATION:
<plain-language explanation>

RUN NEXT:
<commands>
```

For a new empty source file, it is fine to create the path first with only a language-appropriate header comment indicating that generated implementation belongs below it. Replace that placeholder as soon as real code exists; do not accumulate placeholder copies.

## Small-slice rule

One AI response should normally implement one understandable checkpoint. If the task requires several independent ideas, split it before coding.

Good:

```text
BUILD-003A create config model
BUILD-003B load/save config
BUILD-003C connect settings UI
```

Bad:

```text
BUILD-003 finish settings system, redesign UI, migrate storage, add sync
```

## Switching between local AI and ChatGPT

A useful pattern is:

```text
local AI writes one slice
→ you paste it
→ terminal checks it
→ ChatGPT reviews + explains the resulting code/diff
→ you make fixes
→ terminal verifies again
→ Git checkpoint
```

The reviewer should receive the actual resulting code or `git diff`, not merely the original AI answer.

## Never let chat history become project state

Important facts belong in repo docs. At the end of meaningful work update `CURRENT_STATE.md`, `AI_HANDOFF.md`, and any relevant durable decision/bug docs. A new chat should be able to recover the project without needing an old conversation transcript.
