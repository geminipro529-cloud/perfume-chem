"""Operator CLI for the fail-closed Perfume-Chem bridge."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from engine.bridge.canary import run_canary, verify_inventory
from engine.bridge.config import BridgeSettings
from engine.bridge.errors import BridgeBlocked
from engine.bridge.packet_intake import stage_review_packet


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m engine.bridge",
        description="Fail-closed local bridge for the Perfume-Chem repository.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    canary = subparsers.add_parser("canary", help="run a provenance canary")
    canary.add_argument(
        "--mode",
        choices=("metadata", "quick", "full"),
        default="metadata",
    )

    subparsers.add_parser(
        "inventory",
        help="verify the exact Inventory V5 byte and SHA-256 authority",
    )

    stage = subparsers.add_parser(
        "stage",
        help="stage one guarded incoming-review packet without importing MCP",
    )
    stage.add_argument("--packet", required=True, type=Path)
    stage.add_argument("--confirmation", required=True)

    serve = subparsers.add_parser("serve", help="start the optional MCP Streamable HTTP server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = BridgeSettings.from_env()

    if args.command == "canary":
        receipt = run_canary(settings, mode=args.mode)
        _print_json(receipt)
        return 0 if receipt.get("state") in {"READY_FOR_VERIFICATION", "PASS"} else 2

    if args.command == "inventory":
        receipt = verify_inventory(settings)
        _print_json(receipt)
        return 0 if receipt.get("status") == "PASS" else 2

    if args.command == "stage":
        try:
            packet = json.loads(args.packet.read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                raise BridgeBlocked("packet file must contain one JSON object")
            fresh_canary = run_canary(settings, mode="full")
            receipt = stage_review_packet(
                settings,
                packet,
                fresh_canary,
                args.confirmation,
            )
        except (BridgeBlocked, OSError, json.JSONDecodeError) as exc:
            _print_json({"state": "BRIDGE_BLOCKED", "error": str(exc)})
            return 2
        _print_json(receipt)
        return 0

    if args.command == "serve":
        allowed_loopback = {"127.0.0.1", "localhost", "::1"}
        non_loopback_armed = os.getenv("PERFUME_CHEM_ALLOW_NON_LOOPBACK", "").casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if args.host not in allowed_loopback and not non_loopback_armed:
            parser.error(
                "non-loopback binding is blocked; use an authenticated reverse proxy or set "
                "PERFUME_CHEM_ALLOW_NON_LOOPBACK=1 deliberately"
            )
        if not 1 <= args.port <= 65535:
            parser.error("port must be between 1 and 65535")
        try:
            from engine.bridge.server import mcp
        except ModuleNotFoundError as exc:
            if exc.name == "mcp":
                parser.error("optional MCP dependency missing; install requirements-bridge.txt")
            raise
        mcp.run("streamable-http", host=args.host, port=args.port)
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
