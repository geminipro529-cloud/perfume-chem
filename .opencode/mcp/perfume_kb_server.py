r"""MCP server wrapping perfume_kb.jsonl — stdlib only.

Tools:
  query_material(name)        — search by name (odt_*, pw_sku_*, local_inv_*)
  query_family(key)           — search fam_* entries by archetype key
  query_local_inventory()     — return all in_local_inventory=true entries
  query_sku(sku)              — exact match on Perfumer's World SKU

Protocol: JSON-RPC 2.0 over stdio.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


def _resolve_kb_path() -> Path:
    kb_path = os.environ.get("PERFUME_KB_PATH", "")
    if kb_path:
        return Path(kb_path)
    return Path(__file__).resolve().parent.parent / "library" / "perfume_kb.jsonl"


def _load_kb(kb_path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        with open(kb_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        sys.stderr.write(f"[perfume_kb] KB not found at {kb_path}\n")
    return entries


def _log(msg: str) -> None:
    sys.stderr.write(f"[perfume_kb] {msg}\n")


def _send(data: dict) -> None:
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def handle_initialize(msg_id: Any, _params: dict) -> None:
    _send(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "perfume_kb", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }
    )


def handle_tools_list(msg_id: Any, _params: dict) -> None:
    _send(
        {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "query_material",
                        "description": "Search perfume knowledge base for a material by name. Returns top 5 matches across ODT data, Perfumer's World SKUs, and local inventory.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Material name to search (partial match)",
                                },
                            },
                            "required": ["name"],
                        },
                    },
                    {
                        "name": "query_family",
                        "description": "Search fragrance family archetypes by key. Returns matching family entries with their specifications.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "key": {
                                    "type": "string",
                                    "description": "Family archetype key (e.g., 'aromatic_fougere', 'chypre')",
                                },
                            },
                            "required": ["key"],
                        },
                    },
                    {
                        "name": "query_local_inventory",
                        "description": "Return all materials currently in local inventory (in_stock=true).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                    {
                        "name": "query_sku",
                        "description": "Exact lookup of Perfumer's World SKU number. Returns pricing, dilution, and stock info.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "sku": {
                                    "type": "string",
                                    "description": "Perfumer's World SKU (e.g., '4EW14326')",
                                },
                            },
                            "required": ["sku"],
                        },
                    },
                ]
            },
        }
    )


def _fuzzy_match(
    query: str, entries: list[dict], field: str = "name", max_results: int = 5
) -> list[dict]:
    lower = query.lower()
    matches = []
    for entry in entries:
        val = str(entry.get(field, "")).lower()
        if lower in val:
            matches.append(entry)
            if len(matches) >= max_results:
                break
    return matches


def handle_tools_call(entries: list[dict], msg_id: Any, params: dict) -> None:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    try:
        if tool_name == "query_material":
            name = arguments.get("name", "")
            if not name:
                raise ValueError("name is required")
            results = _fuzzy_match(name, entries, "name", 10)
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
                    },
                }
            )

        elif tool_name == "query_family":
            key = arguments.get("key", "")
            if not key:
                raise ValueError("key is required")
            results = [
                e
                for e in entries
                if e.get("id", "").startswith("fam_")
                and key.lower() in str(e.get("key", "")).lower()
            ]
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results[:5], indent=2)}]
                    },
                }
            )

        elif tool_name == "query_local_inventory":
            results = [e for e in entries if e.get("id", "").startswith("local_inv_")]
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
                    },
                }
            )

        elif tool_name == "query_sku":
            sku = arguments.get("sku", "")
            if not sku:
                raise ValueError("sku is required")
            results = [e for e in entries if e.get("sku") == sku]
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
                    },
                }
            )

        else:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {tool_name}"},
                }
            )

    except Exception as exc:
        _send(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Invalid params: {exc}"},
            }
        )


def main() -> None:
    kb_path = _resolve_kb_path()
    _log(f"Loading {kb_path}")
    entries = _load_kb(kb_path)
    _log(f"Loaded {len(entries)} entries")

    initialized = False

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            handle_initialize(msg_id, params)
            initialized = True
        elif method == "notifications/initialized":
            pass  # no response needed
        elif method == "tools/list":
            handle_tools_list(msg_id, params)
        elif method == "tools/call":
            handle_tools_call(entries, msg_id, params)
        else:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )


if __name__ == "__main__":
    main()
