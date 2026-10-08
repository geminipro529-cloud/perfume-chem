# Secure MCP Tunnel — browser ChatGPT Pro edits perfume-chem files without GitHub

**Why this path:** when Codex credits run out, browser ChatGPT Pro can still edit the repo
on this machine through a private tunnel to a local scoped filesystem MCP server. No GitHub,
no Codex tokens — ChatGPT plan + a free tunnel.

## What was already built (this repo)

| Artifact | Path | Purpose |
|---|---|---|
| Filesystem MCP server | `tools/mcp-filesystem/server.mjs` | read_file / write_file / edit_file / list_dir / search_text / file_info, scoped to `D:\chatbots\perfume-chem` |
| MCP SDK deps | `tools/mcp-filesystem/node_modules` | `@modelcontextprotocol/sdk` (installed) |
| Tunnel profile | `tools/mcp-filesystem/perfume-chem-fs.yaml` | canonical project-scoped profile that wires the MCP server into tunnel-client |
| Start script | `tools/mcp-filesystem/start_tunnel.ps1` | validates profile + starts detached daemon |
| Check script | `tools/mcp-filesystem/check_tunnel.ps1` | healthz / readyz / doctor |
| Local test harness | (temp) | verified all 6 tools + escape rejection end-to-end |

Security model (tested): workspace-relative paths only; absolute paths and `..` escapes
rejected; the default root is pinned to this repository regardless of the launch directory;
symlinks are never followed; writes are exact-byte with SHA-256; optional read-only mode via
`FS_MCP_READONLY=1`.

## Step 1 — Create the Tunnel (you, in Platform settings)

1. Open https://platform.openai.com/settings/organization/tunnels
2. Create a tunnel (any name, e.g. `perfume-chem-fs`)
3. Copy the **tunnel ID** (format `tunnel_<32 hex>`)
4. Edit `tools/mcp-filesystem/perfume-chem-fs.yaml` and replace
   `tunnel_00000000000000000000000000000000` with your real ID

## Step 2 — Create a Runtime API key (you)

1. Open https://platform.openai.com/settings/organization/api-keys
2. Create a runtime key (scoped, Tunnels Read + Use)
3. Set it in the environment (permanent):
   ```powershell
   [Environment]::SetEnvironmentVariable("CONTROL_PLANE_API_KEY", "sk-...", "User")
   ```
   (then open a new terminal)

## Step 3 — Start the tunnel

```powershell
.\tools\mcp-filesystem\start_tunnel.ps1
.\tools\mcp-filesystem\check_tunnel.ps1   # expect healthz/readyz OK
```

Local admin UI: http://127.0.0.1:8080/ui

## Step 4 — Connect browser ChatGPT Pro

1. Open https://chatgpt.com/plugins → **+** → create a developer-mode app
2. Connection: **Tunnel** → select the `perfume-chem-fs` tunnel
3. Name it (e.g. "Perfume Chem FS"), save
4. In ChatGPT, start a chat in **Work**, select the app, and prompt e.g.:
   > "Use the Perfume Chem FS app: read `inventory.txt` line 194, then edit
   > `formulas/example.md` replacing X with Y, and report the new SHA-256."

## Step 5 — When Codex credits return

Stop the tunnel when not needed:
```powershell
Get-Process tunnel-client -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Troubleshooting

- `doctor` fails auth → CONTROL_PLANE_API_KEY wrong/missing or tunnel not associated with your
  workspace (Platform org vs ChatGPT workspace association).
- Tunnel not listed in ChatGPT → the tunnel must be associated with the ChatGPT workspace,
  and your account needs Tunnels Read + Use; Enterprise/Edu may require developer-mode access.
- MCP tool errors → run the local test harness again to confirm the server itself is healthy
  (the tunnel only transports; the server does the file work).
- Want read-only guardrails → set `FS_MCP_READONLY: "1"` in the profile's mcp.command env.

Sources: OpenAI Codex docs (Codex cloud / Remote / web surfaces), Secure MCP Tunnel guide
(developers.openai.com/api/docs/guides/secure-mcp-tunnels), and the latest public tunnel-client release.
