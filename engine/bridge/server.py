"""MCP v2 tool adapter for the fail-closed Perfume-Chem bridge."""

from __future__ import annotations

import json
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from engine.bridge.canary import run_canary, verify_inventory
from engine.bridge.config import BridgeSettings
from engine.bridge.packet_intake import stage_review_packet
from engine.bridge.repository import fetch_repository_file, search_repository

mcp = MCPServer("Perfume-Chem Bridge")


def _settings() -> BridgeSettings:
    return BridgeSettings.from_env()


@mcp.tool(
    name="perfume_chem_bridge_status",
    description=(
        "Use this when you need a provenance-bearing status check for the local "
        "Perfume-Chem repository. Metadata mode cannot claim a verified bridge; "
        "quick and full modes invoke the repository-owned acceptance verifier."
    ),
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def perfume_chem_bridge_status(
    mode: Literal["metadata", "quick", "full"] = "metadata",
) -> dict[str, Any]:
    return run_canary(_settings(), mode=mode)


@mcp.tool(
    name="perfume_chem_inventory_authority",
    description=(
        "Use this when you need to verify the exact Inventory V5 file, byte length, "
        "and SHA-256 without exposing workbook contents."
    ),
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def perfume_chem_inventory_authority() -> dict[str, Any]:
    return verify_inventory(_settings())


@mcp.tool(
    name="perfume_chem_search",
    description=(
        "Use this when you need to search allowlisted UTF-8 text inside the local "
        "Perfume-Chem repository. This cannot search secrets, Git internals, databases, "
        "spreadsheets, archives, images, or paths outside the repository."
    ),
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def perfume_chem_search(query: str, limit: int = 20) -> dict[str, Any]:
    return search_repository(_settings(), query, limit=limit)


@mcp.tool(
    name="perfume_chem_fetch",
    description=(
        "Use this when you need one allowlisted UTF-8 repository file after locating it. "
        "The result is byte-limited, path-confined, and read-only."
    ),
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def perfume_chem_fetch(path: str, max_chars: int = 20_000) -> dict[str, Any]:
    return fetch_repository_file(_settings(), path, max_chars=max_chars)


def perfume_chem_stage_review_packet(
    packet_json: str,
    confirmation: str,
) -> dict[str, Any]:
    settings = _settings()
    packet = json.loads(packet_json)
    if not isinstance(packet, dict):
        raise ValueError("packet_json must decode to a JSON object")
    fresh_canary = run_canary(settings, mode="full")
    return stage_review_packet(settings, packet, fresh_canary, confirmation)


if _settings().expose_write_tool:
    perfume_chem_stage_review_packet = mcp.tool(
        name="perfume_chem_stage_review_packet",
        description=(
            "Use this only for an explicit publish or sync request in a workspace that "
            "supports MCP write actions. It reruns the full repository canary and can "
            "create one new signed PACKET.json under the Complex Perfumery inbox. It "
            "never overwrites, promotes, or mutates formulas."
        ),
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )(perfume_chem_stage_review_packet)


app = mcp.streamable_http_app()
