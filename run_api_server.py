#!/usr/bin/env python3
"""
Run the API server with correct Python path setup.
This fixes the "ModuleNotFoundError: No module named 'app'" issue.
"""

import sys
import os
import uvicorn

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add the current directory to Python path
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print("Starting API Server with Python path fix")
print("=" * 60)
print("Python path includes:")
for path in sys.path[:5]:  # Show first 5 paths
    print(f"  - {path}")
if len(sys.path) > 5:
    print(f"  - ... and {len(sys.path) - 5} more")

print("\n" + "=" * 60)
print("Starting uvicorn server...")
print("=" * 60)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )