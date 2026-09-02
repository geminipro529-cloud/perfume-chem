"""Domain errors for the fail-closed Perfume-Chem bridge."""


class BridgeBlocked(RuntimeError):
    """Raised when a bridge operation cannot satisfy every required guard."""
