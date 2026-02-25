from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit


class LogPanel(QWidget):
    """
    What it does:
    - A simple read-only log console.

    Why it matters:
    - Portal automation and DB operations need transparency and debuggability.

    Behavior:
    - append(msg) timestamps the message and adds it to the console.
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Logs"))

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

    def append(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.console.appendPlainText(f"[{ts}] {msg}")