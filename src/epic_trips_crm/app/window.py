from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QLabel,
    QSplitter,
)

from epic_trips_crm.app.widgets.log_panel import LogPanel
from epic_trips_crm.app.widgets.config_status import ConfigStatus


class MainWindow(QMainWindow):
    """
    What it does:
    - Main application window: tabs + log panel + config status.

    Why it matters:
    - Establishes the UI skeleton to plug CRUD + portal workflows into.

    Behavior:
    - Emits log messages to the LogPanel through a simple method (log()).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Epic Trips CRM")
        self.resize(1200, 800)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)

        self.config_status = ConfigStatus()
        layout.addWidget(self.config_status)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, stretch=1)

        # Tabs (functionalities wired in later branches)
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        self.tabs.addTab(self._placeholder_tab("Clients (coming next)"), "Clients")
        self.tabs.addTab(self._placeholder_tab("Trips (coming next)"), "Trips")
        self.tabs.addTab(self._placeholder_tab("Sales (coming next)"), "Sales")
        self.tabs.addTab(self._placeholder_tab("Checklists (coming next)"), "Checklists")
        self.tabs.addTab(self._placeholder_tab("Portal (coming next)"), "Portal")

        # Log panel
        self.log_panel = LogPanel()
        splitter.addWidget(self.log_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        self.log("App started.")

    def _placeholder_tab(self, text: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(label)
        return w

    def log(self, msg: str) -> None:
        self.log_panel.append(msg)