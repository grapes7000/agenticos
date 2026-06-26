# OpenClaw Sandbox for AgenticOS

This folder is the safe starting point for OpenClaw.

Use OpenClaw here first, not across the entire desktop.

## Hard rules

- Do not grant wallet, bank, browser-cookie, password-manager, SSH-key, or seed-phrase access.
- Do not allow automatic file deletion or moving.
- Do not route OpenClaw directly into your full home folder.
- Start with the generated context pack: `context/agenticos-context.md`.
- Have OpenClaw write proposed actions into `output/` before you run anything.

## Good first prompts

Ask OpenClaw:

> Read context/agenticos-context.md and summarize AgenticOS status. Do not change files.

> Read context/agenticos-context.md and propose the next three safe improvements. Write them to output/next-actions.md.

> Create a dry-run plan for improving AgenticOS memory search. Do not run commands.
