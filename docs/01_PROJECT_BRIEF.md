# Project Brief

## Name

AgenticOS

## Purpose

Build a personal Linux control utility that wraps frequently used commands and diagnostic recipes in understandable Python interfaces.

## Primary user

A Linux user who frequently manages workstations, development environments, VPN/Tailscale networking, Docker/self-hosted services, Ollama/local models, and a homelab, and wants fewer memorized commands and more explanatory interfaces.

## Core user experience

The user runs a short command such as `agent network` or `agent docker`. AgenticOS gathers deterministic system facts, classifies health, and presents a compact human explanation rather than raw command output.

## Initial product boundary

The first product is a complete CLI utility. It should develop a broad, reusable set of checks and later explicit safe actions before any TUI or Qt GUI becomes a primary target.

After CLI v1.0:

1. expose the same backend through a TUI;
2. optionally expose it through a PySide6/Qt GUI;
3. use daily operation to discover missing checks/actions;
4. add new capabilities to the CLI/backend first, then surface them in the UIs.

## Why local AI is part of development

Small code slices will be written by local chat models such as Qwen. Prompts should therefore be self-contained and narrow enough that the model can produce working code without repository access or attached files. ChatGPT will review each completed checkpoint and explain the code before development advances.

## Non-goals for the first five checkpoints

- autonomous shell operation;
- destructive fixes;
- a daemon;
- a TUI or Qt GUI;
- LLM-generated truth about system state;
- an abstract plugin framework;
- broad distro management or package installation.
