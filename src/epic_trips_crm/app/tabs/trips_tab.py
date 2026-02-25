from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
from epic_trips_crm.db.repositories.trips import TripRepository


class TripsTab(QWidget):
    """
    What it does:
    - Lists trips (left) and provides a side-panel form to create a new trip (right).

    Why it matters:
    - Trips are your "groups" and the parent entity for sales and checklist workflows.

    Behavior:
    - Refresh pulls latest N trips from Neon.
    - Save creates a new trip and refreshes the table.
    - UI includes ALL fields supported by TripRepository.create().
    """

    STATUSES = ["Próximo", "Viajando", "Finalizado", "Cancelado"]

    def __init__(self, *, log_fn) -> None:
        super().__init__()
        self.log = log_fn

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # LEFT
        left = QVBoxLayout()
        root.addLayout(left, stretch=7)

        header = QHBoxLayout()
        left.addLayout(header)
        header.addWidget(QLabel("Trips"))
        header.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)

        # Updated to include all repository fields
        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Trip Name",
                "Status",
                "Client ID",
                "Start",
                "End",
                "Companions",
                "Flights",
                "Reservation ID",
                "Checklist ID",
                "Notes",
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        left.addWidget(self.table, stretch=1)

        # RIGHT
        right = QVBoxLayout()
        root.addLayout(right, stretch=3)

        right.addWidget(QLabel("Create trip"))

        form = QFormLayout()
        right.addLayout(form)

        self.trip_name = QLineEdit()
        self.client_id = QLineEdit()

        self.status = QComboBox()
        self.status.addItems(self.STATUSES)

        self.start_month = QLineEdit()
        self.start_year = QLineEdit()
        self.end_month = QLineEdit()
        self.end_year = QLineEdit()

        # Missing fields from repository (now included)
        self.companions = QLineEdit()
        self.flights = QLineEdit()
        self.reservation_id = QLineEdit()
        self.checklist_id = QLineEdit()

        self.notes = QLineEdit()

        form.addRow("Trip name*", self.trip_name)
        form.addRow("Status*", self.status)
        form.addRow("Client ID*", self.client_id)

        form.addRow("Start month", self.start_month)
        form.addRow("Start year", self.start_year)
        form.addRow("End month", self.end_month)
        form.addRow("End year", self.end_year)

        form.addRow("Companions", self.companions)
        form.addRow("Flights", self.flights)
        form.addRow("Reservation ID", self.reservation_id)
        form.addRow("Checklist ID", self.checklist_id)

        form.addRow("Notes", self.notes)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.create_trip)
        right.addWidget(self.btn_save)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_form)
        right.addWidget(self.btn_clear)

        right.addStretch(1)

        self.refresh()

    def clear_form(self) -> None:
        self.trip_name.clear()
        self.client_id.clear()
        self.start_month.clear()
        self.start_year.clear()
        self.end_month.clear()
        self.end_year.clear()
        self.companions.clear()
        self.flights.clear()
        self.reservation_id.clear()
        self.checklist_id.clear()
        self.notes.clear()
        self.status.setCurrentIndex(0)

    def refresh(self) -> None:
        try:
            with get_session() as session:
                repo = TripRepository(session)
                trips = repo.list(limit=200)

            self.table.setRowCount(0)
            for t in trips:
                r = self.table.rowCount()
                self.table.insertRow(r)

                self.table.setItem(r, 0, QTableWidgetItem(str(t.id)))
                self.table.setItem(r, 1, QTableWidgetItem(t.trip_name or ""))
                self.table.setItem(
                    r, 2, QTableWidgetItem(str(t.status) if t.status is not None else "")
                )
                self.table.setItem(r, 3, QTableWidgetItem(str(t.client_id)))

                self.table.setItem(
                    r, 4, QTableWidgetItem(f"{t.start_month or ''} {t.start_year or ''}".strip())
                )
                self.table.setItem(
                    r, 5, QTableWidgetItem(f"{t.end_month or ''} {t.end_year or ''}".strip())
                )

                self.table.setItem(r, 6, QTableWidgetItem(t.companions or ""))
                self.table.setItem(r, 7, QTableWidgetItem(t.flights or ""))
                self.table.setItem(
                    r,
                    8,
                    QTableWidgetItem("" if t.reservation_id is None else str(t.reservation_id)),
                )
                self.table.setItem(
                    r, 9, QTableWidgetItem("" if t.checklist_id is None else str(t.checklist_id))
                )
                self.table.setItem(r, 10, QTableWidgetItem(t.notes or ""))

            self.log(f"Trips refreshed: {len(trips)}")
        except Exception as e:
            self.log(f"ERROR refreshing trips: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh trips:\n{e}")

    def create_trip(self) -> None:
        name = self.trip_name.text().strip()
        status = self.status.currentText()
        client_id_raw = self.client_id.text().strip()

        if not name or not client_id_raw:
            QMessageBox.warning(self, "Validation", "Trip name and Client ID are required.")
            return

        try:
            client_id = int(client_id_raw)
        except ValueError:
            QMessageBox.warning(self, "Validation", "Client ID must be an integer.")
            return

        start_month = self.start_month.text().strip() or None
        end_month = self.end_month.text().strip() or None

        start_year_raw = self.start_year.text().strip()
        end_year_raw = self.end_year.text().strip()

        try:
            start_year = int(start_year_raw) if start_year_raw else None
        except ValueError:
            QMessageBox.warning(self, "Validation", "Start year must be an integer.")
            return

        try:
            end_year = int(end_year_raw) if end_year_raw else None
        except ValueError:
            QMessageBox.warning(self, "Validation", "End year must be an integer.")
            return

        companions = self.companions.text().strip() or None
        flights = self.flights.text().strip() or None

        reservation_id_raw = self.reservation_id.text().strip()
        checklist_id_raw = self.checklist_id.text().strip()

        try:
            reservation_id = int(reservation_id_raw) if reservation_id_raw else None
        except ValueError:
            QMessageBox.warning(self, "Validation", "Reservation ID must be an integer.")
            return

        try:
            checklist_id = int(checklist_id_raw) if checklist_id_raw else None
        except ValueError:
            QMessageBox.warning(self, "Validation", "Checklist ID must be an integer.")
            return

        notes = self.notes.text().strip() or None

        try:
            with get_session() as session:
                repo = TripRepository(session)
                repo.create(
                    trip_name=name,
                    status=status,
                    client_id=client_id,
                    start_month=start_month,
                    start_year=start_year,
                    end_month=end_month,
                    end_year=end_year,
                    companions=companions,
                    flights=flights,
                    reservation_id=reservation_id,
                    notes=notes,
                    checklist_id=checklist_id,
                )

            self.log(f"Created trip: {name} (client_id={client_id})")
            self.clear_form()
            self.refresh()
        except Exception as e:
            self.log(f"ERROR creating trip: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create trip:\n{e}")
