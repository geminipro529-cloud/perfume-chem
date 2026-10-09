# Tools, MCP servers and OpenCode agents

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Agentic Workflow (for DeepSeek)

When tasks involve multiple domains (e.g., research + code + test), break them into sub-tasks using `sequential_thinking` first, then use `rg` and the built-in search tools for research before writing code. This compensates for DeepSeek's tendency to shortcut complex reasoning chains.

## Tool usage rules

MCP servers configured in `opencode.json`: `github`, `playwright`, `sequential_thinking`, `pubchem`, `memory`, `perfume_kb`, `cheapluna`. Use only these.
Use `github` for GitHub code patterns, `sequential_thinking` for step-by-step decomposition, and `pubchem` for compound data (MW, logP, VP, ODT, CAS).
For docs, code search and project structure, use the built-in tools and `rg`.

## Agents for synergy/pairing discovery

Use `@agent-citrus-top` for citrus, green, and top-note material pairings.
Use `@agent-floral-heart` for floral and heart-note material pairings.
Use `@agent-woody-base` for woody, amber, and base-structure material pairings.
Use `@agent-musk-fixative` for musk, fixative, gourmand, and leather material pairings.
Use `@agent-spice-aromatic` for spice, aromatic, and specialty material pairings.

Each agent reads `inventory.txt`, evaluates pairs against perfumery + chemistry criteria, and appends findings to `data/knowledge_graph/pairing_rules_discovered.json`. Run all 5 agents in parallel to cover the full inventory.

## Token efficiency

MCP servers consume context tokens just by being loaded. Only invoke them when they will provide concrete benefit — do not call them reflexively. Prefer built-in tools (`read`, `grep`, `glob`, `bash`) for simple queries; save MCP calls for cases where they genuinely add value (cross-referencing external code, searching docs, deep architecture mapping).

## Tools & Token Optimization

### MCP Toggle Script

**Windows/PowerShell only; it cannot run under Claude Code on Linux.** `scripts/toggle-mcp.ps1` manages which MCP servers are loaded. Each active MCP consumes context tokens — disable unused ones to maximize token budget.

```powershell
# View current MCP status
.\scripts\toggle-mcp.ps1 -Status

# Apply named profiles:
.\scripts\toggle-mcp.ps1 -Profile formula   # chemistry/formula work (pubchem+memory+seq on, rest off)
.\scripts\toggle-mcp.ps1 -Profile dev       # full development (all on)
.\scripts\toggle-mcp.ps1 -Profile minimal   # maximum token efficiency (all off)

# Toggle specific MCPs:
.\scripts\toggle-mcp.ps1 -Enable github,playwright
.\scripts\toggle-mcp.ps1 -Disable playwright
```

**Restart OpenCode after toggling** for changes to take effect.

### MCP Server Profiles

| Profile | github | playwright | seq_think | pubchem | memory | Best for |
|---------|--------|------------|-----------|---------|--------|----------|
| `formula` | OFF | OFF | ON | ON | ON | Formula gating, material analysis, chemistry work |
| `dev` | ON | ON | ON | ON | ON | Full development, PRs, code changes |
| `minimal` | OFF | OFF | OFF | OFF | OFF | Max token efficiency, simple queries |
| `full` | ON | ON | ON | ON | ON | Same as dev |

### Token Optimization Strategy

**MCP servers consume context tokens just by being loaded.** Each active MCP adds its tool definitions to the system prompt. For maximum token efficiency:

1. **Formula/chemistry sessions**: Use `formula` profile. You rarely need GitHub or Playwright when gating formulas or analyzing OAV data.
2. **Code development sessions**: Use `dev` profile (or toggle on needed MCPs individually).
3. **Quick lookups**: Use `minimal` profile if the built-in tools (grep, glob, read) suffice.

**High-impact toggles**: `playwright` and `github` are the heaviest token consumers. Disable them first when not needed.

### Available Tools Overview

| Tool | Type | Use when |
|------|------|----------|
| `grep` | Built-in | Content search in codebase |
| `glob` | Built-in | File pattern matching |
| `rg` (ripgrep) | Shell | Fast regex search (already installed: 15.1.0) |
| `sg` (ast-grep) | Shell/skill | AST-aware structural search (0.43.0) |
| `basedpyright` | LSP | Python type checking (1.39.8, configured as default) |
| `ruff` | Formatter | Python formatting |
| `gh` | Shell | GitHub CLI operations (2.95.0) |
| `npx` | Shell | Node package runner (11.16.0) |
| `docker compose` | Shell | Container management |

### MCP Servers Reference

| MCP | Package | Purpose | Token cost |
|-----|---------|---------|------------|
| `github` | `@modelcontextprotocol/server-github` | Code search, PRs, issues, repo ops | High |
| `playwright` | `@playwright/mcp` | Browser automation, web testing | High |
| `sequential_thinking` | `@modelcontextprotocol/server-sequential-thinking` | Multi-step reasoning | Medium |
| `pubchem` | `@cyanheads/pubchem-mcp-server` | Chemical compound data (MW, logP, VP, ODT) | Medium |
| `memory` | `@modelcontextprotocol/server-memory` | Persistent knowledge graph | Low-Medium |

### LSP

The workspace uses **basedpyright** (1.39.8) for Python type checking, configured in `opencode.json`. It replaces the deprecated `pyright`. Both `.py` and `.pyi` files are covered.
