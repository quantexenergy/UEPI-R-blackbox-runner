"""Load the sealed core or fall back to the demo detector."""
from __future__ import annotations

import sys
from types import ModuleType


def load_core() -> ModuleType:
    """Try to import uepi_core; fall back to demo_core with a warning."""
    try:
        import uepi_core
        return uepi_core
    except ImportError:
        print(
            "WARNING: uepi_core wheel not installed — using DEMO detector.\n"
            "  Demo mode produces intentionally worse metrics.\n"
            "  To install the verified core, run:\n"
            "    python scripts/install_core.py\n"
            "  (requires GH_TOKEN with read access to the private repo)\n",
            file=sys.stderr,
        )
        from uepi_runner import demo_core
        return demo_core


def is_verified_core(core: ModuleType) -> bool:
    """Check whether we have the real core or the demo fallback."""
    return core.__name__ == "uepi_core"
