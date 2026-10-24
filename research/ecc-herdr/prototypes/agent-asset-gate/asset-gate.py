#!/usr/bin/env python
"""Entry point usable under `python -I` (isolated mode): adds its own directory to sys.path explicitly.

    python -I C:\\Herdr-dev\\prototypes\\agent-asset-gate\\asset-gate.py scan <path> [--json out] [--md out]
    python -I C:\\Herdr-dev\\prototypes\\agent-asset-gate\\asset-gate.py coexist <settings.json>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asset_gate.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
