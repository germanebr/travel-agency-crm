from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from epic_trips_crm.app.window import MainWindow


def main() -> int:
    """
    What it does:
    - Bootstraps the PySide6 QApplication and shows the main window.

    Why it matters:
    - Provides the canonical entrypoint for running the GUI locally and later from the exe.

    Behavior:
    - Returns the Qt event loop exit code.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())