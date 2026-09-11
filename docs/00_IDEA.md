# Idea

## Problem

I accumulate useful Linux commands, diagnostics, and multi-step recipes across system setup, networking, Tailscale/Mullvad, Docker/self-hosting, Ollama/local AI, Git, Python environments, and development work. They are often hard to remember, difficult to interpret, and easy to lose in chat history.

## Product idea

Turn those recipes into named Python checks and actions that expose one intuitive `agent` CLI. The utility should translate raw Linux state into concise human language so I can understand what is healthy, what is wrong, why it matters, and what I can do next.

Examples:

```bash
agent status
agent network
agent system
agent docker
agent ollama
agent dev
agent homelab
```

The CLI should become the canonical backend and source of truth. Once it is complete enough, the same Python capabilities can be surfaced through a TUI, a PySide6/Qt GUI, local-AI tools, and optional background health checks.

## Product principle

**Turn personal Linux knowledge into reusable software instead of repeatedly rediscovering commands.**

## First milestone

A working `agent status` command that runs several safe read-only checks, returns consistent structured results, and renders them clearly with Rich.
