#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn


def main() -> None:
    inventory_authority = os.environ.get("PERFUME_CHEM_V5_INVENTORY")
    if inventory_authority:
        os.environ.setdefault("SOLFORGE_INVENTORY_PATH", inventory_authority)
        os.environ.setdefault(
            "PERFUME_COMPLEXITY_INVENTORY_WORKBOOK",
            inventory_authority,
        )
    backend_dir = Path(__file__).resolve().parent / "backend"
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
        app_dir=str(backend_dir),
    )


if __name__ == "__main__":
    main()
