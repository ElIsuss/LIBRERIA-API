#!/usr/bin/env python3
"""Launcher script for Change 08 seed functionality.

Executes the seed script from the app.seed module.
Usage: python seed.py (from project root)
"""

import asyncio
import sys
import os

# Ensure the project root (containing 'app/') is on sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.seed import seed


async def main() -> None:
    await seed()


if __name__ == "__main__":
    asyncio.run(main())