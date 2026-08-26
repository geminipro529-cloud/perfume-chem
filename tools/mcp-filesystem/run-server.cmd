@echo off
rem Launcher for the perfume-chem scoped filesystem MCP server (used by tunnel-client).
rem tunnel-client's stdio command field takes a single executable path; this wrapper
rem carries the node + script arguments so the YAML stays schema-valid.
"C:\Program Files\nodejs\node.exe" "D:\chatbots\perfume-chem\tools\mcp-filesystem\server.mjs" %*
