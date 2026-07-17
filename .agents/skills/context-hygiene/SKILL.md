---
name: context-hygiene
description: Use for large Perfume-Chem investigations and long-running tasks to reduce token and wall-clock cost without losing relevant repository context.
---

# Context Hygiene

1. Search names and symbols with `rg`; read bounded line ranges instead of whole large files.
2. Parallelize independent local reads, not dependent edits or external calls.
3. Exclude generated directories, caches, virtual environments, and `node_modules` from scans.
4. Reuse current official-doc caches and prior command output when the underlying inputs are unchanged.
5. Keep delegated prompts stable and self-contained; append volatile repository state last.
6. Load only the plugin, MCP, skill body, or reference needed for the current evidence gap.
7. Summarize long tool output into durable evidence before compaction.
