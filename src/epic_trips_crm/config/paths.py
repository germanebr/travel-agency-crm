from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """
    Returns the base directory for runtime files.

    - In dev: repo root-ish (relative to this file)
    - In PyInstaller: directory containing the executable
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as a bundled executable
        return Path(sys.executable).resolve().parent

    # Running from source: .../src/epic_trips_crm/config/paths.py -> repo root is 3 parents up
    return Path(__file__).resolve().parents[3]


def env_file_path() -> Path:
    return app_base_dir() / ".env"
