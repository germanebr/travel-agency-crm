from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from epic_trips_crm.db.engine import get_session
from epic_trips_crm.db.repositories.clients import ClientRepository


class ClientsTab(QWidget):
    """
    What it does:
    - Lists clients (left) and provides a side-panel form to create a new client (right).

    Why it matters:
    - This is core CRUD needed before portal automation can reliably create travelers.

    Behavior:
    - Refresh pulls latest N clients from Neon.
    - Save creates a new client and refreshes the table.
    """

    def __init__(self, *, log_fn) -> None:
        super().__init__()
        self.log = log_fn

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # LEFT: table + actions
        left = QVBoxLayout()
        root.addLayout(left, stretch=7)

        header = QHBoxLayout()
        left.addLayout(header)

        header.addWidget(QLabel("Clients"))
        header.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "First Name", "Last Name", "Email", "Phone", "Country", "Address"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        left.addWidget(self.table, stretch=1)

        # RIGHT: side-panel form
        right = QVBoxLayout()
        root.addLayout(right, stretch=3)

        right.addWidget(QLabel("Create client"))

        form = QFormLayout()
        right.addLayout(form)

        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        self.country = QLineEdit()
        self.address = QLineEdit()

        form.addRow("First name*", self.first_name)
        form.addRow("Last name*", self.last_name)
        form.addRow("Email*", self.email)
        form.addRow("Phone", self.phone)
        form.addRow("Country", self.country)
        form.addRow("Address", self.address)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.create_client)
        right.addWidget(self.btn_save)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_form)
        right.addWidget(self.btn_clear)

        right.addStretch(1)

        # Initial load
        self.refresh()

    def clear_form(self) -> None:
        self.first_name.clear()
        self.last_name.clear()
        self.email.clear()
        self.phone.clear()
        self.country.clear()
        self.address.clear()

    def refresh(self) -> None:
        try:
            with get_session() as session:
                repo = ClientRepository(session)
                # If you don't have repo.list(), implement your repository list or use a query method you already have.
                # We'll assume list(limit=...) exists; if not, tell me and I’ll adapt.
                clients = repo.list(limit=200)

            self.table.setRowCount(0)
            for c in clients:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(str(c.id)))
                self.table.setItem(r, 1, QTableWidgetItem(c.first_name or ""))
                self.table.setItem(r, 2, QTableWidgetItem(c.last_name or ""))
                self.table.setItem(r, 3, QTableWidgetItem(c.email or ""))
                self.table.setItem(r, 4, QTableWidgetItem(c.phone or ""))
                self.table.setItem(r, 5, QTableWidgetItem(c.country or ""))
                self.table.setItem(r, 6, QTableWidgetItem(c.address or ""))

            self.log(f"Clients refreshed: {len(clients)}")
        except Exception as e:
            self.log(f"ERROR refreshing clients: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh clients:\n{e}")

    def create_client(self) -> None:
        fn = self.first_name.text().strip()
        ln = self.last_name.text().strip()
        em = self.email.text().strip()
        ph = self.phone.text().strip() or None
        co = self.country.text().strip() or None
        ad = self.address.text().strip() or None

        if not fn or not ln or not em:
            QMessageBox.warning(
                self, "Validation", "First name, last name, and email are required."
            )
            return

        try:
            with get_session() as session:
                repo = ClientRepository(session)
                repo.create(
                    first_name=fn,
                    last_name=ln,
                    email=em,
                    phone=ph,
                    country=co,
                    address=ad,
                )

            self.log(f"Created client: {fn} {ln} ({em})")
            self.clear_form()
            self.refresh()
        except Exception as e:
            self.log(f"ERROR creating client: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create client:\n{e}")
