"""Fail-closed local bridge for the Perfume-Chem repository."""

from engine.bridge.canary import run_canary, verify_inventory
from engine.bridge.config import BridgeSettings
from engine.bridge.errors import BridgeBlocked

__all__ = ["BridgeBlocked", "BridgeSettings", "run_canary", "verify_inventory"]
__version__ = "1.0.0"
