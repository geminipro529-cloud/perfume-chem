#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

from pathlib import Path

import uvicorn


def main() -> None:
    backend_dir = Path(__file__).resolve().parent / "backend"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        app_dir=str(backend_dir),
    )


if __name__ == "__main__":
    main()
