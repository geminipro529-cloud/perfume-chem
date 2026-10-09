@echo off
rem Launcher for the perfume-chem scoped filesystem MCP server (local use only; it does
rem not open a tunnel). The server listens on http://127.0.0.1:8765/mcp, is read-only
rem unless --allow-writes is passed, and prints a fresh bearer token once unless
rem FS_MCP_TOKEN is set. To expose it to ChatGPT use start_tunnel.ps1 instead.
"C:\Program Files\nodejs\node.exe" "D:\chatbots\perfume-chem\tools\mcp-filesystem\server.mjs" %*
