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
| Tests | `tools/mcp-filesystem/test/` | `npm test`: token, read-only default, deny-list, escapes |

Security model (tested by `npm test`):

- **Public URL, bearer token.** The tunnel URL is public. `start_tunnel.ps1` starts the server
  on `http://127.0.0.1:8765/mcp` with a fresh random token per launch (`FS_MCP_TOKEN`, held
  only in that PowerShell session's environment) and tunnel-client sends it as
  `Authorization: Bearer <token>` from `env:FS_MCP_AUTH_HEADER` (see the yaml). Any request
  without the right token gets a bare 401. The token is never written to a file; the script
  prints it once. The script refuses to open the tunnel if the profile uses a stdio
  `commands` entry or the server is not rejecting tokenless requests. Run on its own
  (`node server.mjs` / `run-server.cmd`), the server prints a new token once unless
  `FS_MCP_TOKEN` (32+ characters) is set.
- **Read-only by default.** `write_file` and `edit_file` are refused unless the server is
  started with `FS_MCP_ALLOW_WRITES=1` or `--allow-writes` (`start_tunnel.ps1 -AllowWrites`).
  `FS_MCP_READONLY=1` still forces read-only.
- **Deny-list** for every read, write, listing and search, checked on the requested path and
  again after resolving symlinks, case-insensitively and with either slash style: `.env`,
  `.env.*`, `*.pem`, `*.key`, names containing `openai-api-key`, `error.log`, and everything
  under `.git/`. Denied names are left out of `list_dir` and `search_text` results.
- Workspace-relative paths only; absolute paths, `..` escapes and symlinks that resolve outside
  the workspace are rejected; the default root is pinned to this repository; writes are
  exact-byte with SHA-256.

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
.\tools\mcp-filesystem\start_tunnel.ps1                # read-only
.\tools\mcp-filesystem\start_tunnel.ps1 -AllowWrites   # only when ChatGPT must edit files
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

Stop the tunnel and the server when not needed (pids are printed by `start_tunnel.ps1`):
```powershell
Stop-Process -Id <TUNNEL pid>, <SERVER pid> -Force
```

## Troubleshooting

- `doctor` fails auth → CONTROL_PLANE_API_KEY wrong/missing or tunnel not associated with your
  workspace (Platform org vs ChatGPT workspace association).
- Tunnel not listed in ChatGPT → the tunnel must be associated with the ChatGPT workspace,
  and your account needs Tunnels Read + Use; Enterprise/Edu may require developer-mode access.
- MCP tool errors → run `npm test` here to confirm the server itself is healthy
  (the tunnel only transports; the server does the file work).
- Every MCP call fails with 401 → the server and tunnel-client were not started from the same
  `start_tunnel.ps1` run (stop both and rerun it), or the connector is forwarding its own
  `Authorization` header, which overrides the static one; keep the ChatGPT app on no auth.
- `check_tunnel.ps1` doctor complains about `FS_MCP_AUTH_HEADER` → expected in a new terminal;
  that variable only exists inside the session that ran `start_tunnel.ps1`.

Sources: OpenAI Codex docs (Codex cloud / Remote / web surfaces), Secure MCP Tunnel guide
(developers.openai.com/api/docs/guides/secure-mcp-tunnels), and the latest public tunnel-client release.
