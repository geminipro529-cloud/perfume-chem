"""Call any MCP server from the command line.
Usage:
    python scripts/mcp_call.py <server> <method> [params_json]
    python scripts/mcp_call.py pubchem tools/list
    python scripts/mcp_call.py pubchem tools/call '{"name":"pubchem_search_compound_by_identifier","arguments":{"identifierType":"name","identifiers":["rhodinol"]}}'
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# Load .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
NPX = os.environ.get("NPX_CMD", r"C:\Program Files\nodejs\npx.cmd")

def _cmd(server, *args):
    """Build a shell command for an MCP server."""
    qnpx = '"' + NPX + '"'
    local_cmds = {
        "pubchem": (qnpx + " -y @cyanheads/pubchem-mcp-server", "subprocess"),
        "filesystem": (qnpx + " -y @modelcontextprotocol/server-filesystem", "subprocess"),
        "git": (qnpx + " -y @modelcontextprotocol/server-git", "subprocess"),
        "fetch": (qnpx + " -y @modelcontextprotocol/server-fetch", "subprocess"),
        "playwright": (qnpx + " -y @playwright/mcp", "subprocess"),
        "github": (qnpx + " -y @modelcontextprotocol/server-github", "subprocess"),
        "repomap_mcp": (qnpx + " -y repomap-mcp-server", "subprocess"),
        "repomap_bin": (r'"C:\Users\Kenny\AppData\Roaming\npm\node_modules\repomap-bin\node_modules\@gjczone\repomap-windows-x64\repomap.exe"', "cli"),
        "sequential_thinking": (["python", str(ROOT / "scripts" / "sequential_thinking.py")], "cli"),
    }
    remote_endpoints = {
        "context7": "https://mcp.context7.com/mcp",
        "grep": "https://mcp.grep.app",
    }
    if server in remote_endpoints:
        return (remote_endpoints[server], "remote")
    return local_cmds.get(server, (server, "subprocess"))

MCP_ENV = {
    "pubchem": {},
    "filesystem": {},
    "git": {},
    "fetch": {},
    "playwright": {},
    "github": {"GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", "")},
    "repomap_mcp": {"REPOMAP_BIN": r"C:\Users\Kenny\AppData\Roaming\npm\node_modules\repomap-bin\node_modules\@gjczone\repomap-windows-x64\repomap.exe"},
    "repomap_bin": {},
    "sequential_thinking": {},
}

REMOTE_HEADERS = {
    "context7": {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "CONTEXT7_API_KEY": os.environ.get("CONTEXT7_API_KEY", ""),
    },
    "grep": {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    },
}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    server_name = sys.argv[1]
    method = sys.argv[2]
    if len(sys.argv) > 3:
        params = json.loads(sys.argv[3])
    elif not sys.stdin.isatty():
        params = json.loads(sys.stdin.read())
    else:
        params = {}

    cmd, ctype = _cmd(server_name)
    if not cmd:
        print(f"Unknown MCP server: {server_name}")
        print("Available: pubchem, filesystem, git, fetch, playwright, github, repomap_bin, sequential_thinking, context7, grep")
        sys.exit(1)

    if ctype == "remote":
        # Remote MCP via HTTP POST (SSE transport)
        req_data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        headers = REMOTE_HEADERS.get(server_name, {"Content-Type": "application/json"})
        try:
            req = urllib.request.Request(cmd, data=req_data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=30)
            raw = resp.read().decode("utf-8", errors="replace")
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    text = line[6:]
                    # Try to pretty-print as JSON, else raw
                    try:
                        d = json.loads(text)
                        print(json.dumps(d, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(text)
                elif line.strip():
                    try:
                        print(json.dumps(json.loads(line), indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(line)
            return
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    env = {**os.environ, **MCP_ENV.get(server_name, {})}

    if ctype == "cli":
        if isinstance(cmd, list):
            subprocess.run(cmd + ([method] if method != "tools/list" else []), env=env)
        else:
            full_cmd = cmd + (" " + method if method != "tools/list" else "")
            subprocess.run(full_cmd, shell=True, env=env)
        return

    # MCP mode via stdio
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}) + "\n"
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", env=env, shell=True,
        )
        out, err = proc.communicate(input=req, timeout=30)
        for line in out.strip().split("\n"):
            if line.startswith("data: "):
                print(json.dumps(json.loads(line[6:]), indent=2, ensure_ascii=False))
            elif line.strip():
                try:
                    print(json.dumps(json.loads(line), indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(line)
        if err:
            print("STDERR:", err[:500], file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("Error: MCP server timed out", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
