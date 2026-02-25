from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from epic_trips_crm.app.tabs.checklists_tab import ChecklistsTab
from epic_trips_crm.app.tabs.clients_tab import ClientsTab
from epic_trips_crm.app.tabs.sales_tab import SalesTab
from epic_trips_crm.app.tabs.trips_tab import TripsTab
from epic_trips_crm.app.widgets.config_status import ConfigStatus
from epic_trips_crm.app.widgets.log_panel import LogPanel


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

        # 1) Create log panel FIRST
        self.log_panel = LogPanel()
        splitter.addWidget(self.log_panel)

        # 2) Create tabs AFTER log panel exists
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # (Optional) Put tabs on top and logs on bottom by swapping add order:
        # - add tabs first, then log panel, but still instantiate log_panel before tabs.
        # We'll keep visual order: tabs top, logs bottom:
        splitter.insertWidget(0, self.tabs)
        splitter.insertWidget(1, self.log_panel)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        # Replace placeholder Clients with real tab
        self.tabs.addTab(ClientsTab(log_fn=self.log), "Clients")
        self.tabs.addTab(TripsTab(log_fn=self.log), "Trips")
        self.tabs.addTab(SalesTab(log_fn=self.log), "Sales")
        self.tabs.addTab(ChecklistsTab(log_fn=self.log), "Checklists")

        # Keep placeholders for now (we’ll implement next)
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
        if hasattr(self, "log_panel") and self.log_panel is not None:
            self.log_panel.append(msg)
