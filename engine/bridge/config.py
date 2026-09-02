"""Immutable configuration for the fail-closed Perfume-Chem bridge."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

INVENTORY_V5_SHA256 = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
INVENTORY_V5_BYTES = 199_635
DEFAULT_CONVERSATION_ID = "6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf"
DEFAULT_REPOSITORY = "geminipro529-cloud/perfume-chem"
DEFAULT_REPO_ROOT = Path(r"D:\chatbots\perfume-chem")
DEFAULT_INVENTORY_NAME = "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"
DEFAULT_PROTOCOL_PATH = Path("chat_bridge/complex_perfumery/PROTOCOL.md")
DEFAULT_READ_PREFIXES = (
    "docs",
    "engine",
    "backend",
    "schemas",
    "configs",
    "formulas",
    "chat_bridge/complex_perfumery",
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _path_list(raw: str | None, default: tuple[Path, ...]) -> tuple[Path, ...]:
    if not raw:
        return default
    return tuple(Path(item) for item in raw.split(os.pathsep) if item.strip())


@dataclass(frozen=True, slots=True)
class BridgeSettings:
    """All operator-controlled bridge settings, resolved before an operation."""

    repo_root: Path
    expected_repository: str
    inventory_path: Path
    inventory_sha256: str
    inventory_bytes: int
    protocol_relative_path: Path
    protocol_sha256: str | None
    conversation_id: str
    packet_writes_enabled: bool
    signing_key: bytes | None
    verify_timeout_seconds: int
    allowed_read_prefixes: tuple[str, ...]
    max_read_bytes: int
    forbidden_roots: tuple[Path, ...]
    expose_write_tool: bool = False

    @classmethod
    def from_env(cls) -> "BridgeSettings":
        repo_root = Path(os.getenv("PERFUME_CHEM_REPO_ROOT", str(DEFAULT_REPO_ROOT)))
        inventory_path = Path(
            os.getenv(
                "PERFUME_CHEM_INVENTORY_PATH",
                str(repo_root / DEFAULT_INVENTORY_NAME),
            )
        )
        signing_key_text = os.getenv("PERFUME_CHEM_BRIDGE_SIGNING_KEY")
        protocol_hash = os.getenv("PERFUME_CHEM_PROTOCOL_SHA256")
        default_forbidden = (
            Path(r"D:\3_way_nano_drug_project"),
            Path(r"D:\3_way_nano_drug_cancer"),
        )
        prefixes_raw = os.getenv("PERFUME_CHEM_READ_PREFIXES")
        if prefixes_raw:
            requested_prefixes = {
                item.strip().replace("\\", "/")
                for item in prefixes_raw.split(",")
                if item.strip()
            }
            prefixes = tuple(
                prefix for prefix in DEFAULT_READ_PREFIXES if prefix in requested_prefixes
            )
        else:
            prefixes = DEFAULT_READ_PREFIXES
        extra_forbidden = _path_list(
            os.getenv("PERFUME_CHEM_FORBIDDEN_ROOTS"), ()
        )
        return cls(
            repo_root=repo_root,
            expected_repository=DEFAULT_REPOSITORY,
            inventory_path=inventory_path,
            inventory_sha256=INVENTORY_V5_SHA256,
            inventory_bytes=INVENTORY_V5_BYTES,
            protocol_relative_path=DEFAULT_PROTOCOL_PATH,
            protocol_sha256=protocol_hash.lower() if protocol_hash else None,
            conversation_id=DEFAULT_CONVERSATION_ID,
            packet_writes_enabled=_env_bool("PERFUME_CHEM_PACKET_WRITES"),
            signing_key=signing_key_text.encode("utf-8") if signing_key_text else None,
            verify_timeout_seconds=_env_int(
                "PERFUME_CHEM_VERIFY_TIMEOUT_SECONDS",
                1_200,
                minimum=10,
                maximum=7_200,
            ),
            allowed_read_prefixes=prefixes,
            max_read_bytes=_env_int(
                "PERFUME_CHEM_MAX_READ_BYTES",
                256 * 1024,
                minimum=1_024,
                maximum=2 * 1024 * 1024,
            ),
            forbidden_roots=default_forbidden + extra_forbidden,
            expose_write_tool=_env_bool("PERFUME_CHEM_EXPOSE_WRITE_TOOL"),
        )

    def with_overrides(self, **changes: Any) -> "BridgeSettings":
        """Return a test- or operator-scoped copy without mutating this object."""

        return replace(self, **changes)
