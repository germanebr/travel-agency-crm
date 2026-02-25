from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

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
from epic_trips_crm.db.repositories.sales import SaleRepository


class SalesTab(QWidget):
    """
    What it does:
    - Lists sales (left) and provides a side-panel form to create a new sale (right).

    Why it matters:
    - Sales drive portal submissions and trip status sync logic.

    Behavior:
    - Minimal required fields to create a sale are enforced.
    """

    PROVIDERS = [
        "Aeromexico",
        "Agent Cars",
        "Bedsonline",
        "Civitatis",
        "Creatur",
        "Disney",
        "Expedia MX",
        "Expedia USA",
        "GRUPO LOMAS",
        "Room res",
        "Terrawind",
        "VAX",
        "Vacation Express",
        "Viator",
        "Virgin",
        "Xcaret Sales",
    ]

    STATUSES = ["Reservada", "Liquidada", "Completa", "Cancelada", "No aplica"]

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
        header.addWidget(QLabel("Sales"))
        header.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(self.btn_refresh)

        self.table = QTableWidget(0, 27)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Status",
                "Client ID",
                "Trip ID",
                "Provider",
                "Booking",
                "Start",
                "End",
                "Destination",
                "Concept",
                "Hotel",
                "Room type",
                "Adults",
                "Children",
                "Conf #",
                "Total",
                "Client payments",
                "Balance",
                "Payment deadline",
                "Park days",
                "Ticket type",
                "Photos",
                "Express passes",
                "Meal plan",
                "Promotion",
                "Extras",
                "App account",
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        left.addWidget(self.table, stretch=1)

        # RIGHT
        right = QVBoxLayout()
        root.addLayout(right, stretch=3)

        right.addWidget(QLabel("Create sale"))

        form = QFormLayout()
        right.addLayout(form)

        self.status = QComboBox()
        self.status.addItems(self.STATUSES)

        self.provider = QComboBox()
        self.provider.addItems(self.PROVIDERS)

        self.client_id = QLineEdit()
        self.trip_id = QLineEdit()

        # ISO dates (YYYY-MM-DD). Your DB columns are date.
        self.travel_start = QLineEdit()
        self.travel_end = QLineEdit()

        self.confirmation_number = QLineEdit()
        self.total_amount = QLineEdit()

        self.booking_date = QLineEdit()  # YYYY-MM-DD
        self.destination = QLineEdit()
        self.concept = QLineEdit()
        self.hotel = QLineEdit()
        self.room_type = QLineEdit()
        self.adults = QLineEdit()  # int
        self.children_edit = QLineEdit()

        self.client_payments = QLineEdit()  # Decimal
        self.balance_amount = QLineEdit()  # Decimal
        self.payment_deadline = QLineEdit()  # YYYY-MM-DD

        self.park_days = QLineEdit()  # int
        self.ticket_type = QLineEdit()

        self.photos = QLineEdit()
        self.express_passes = QLineEdit()
        self.meal_plan = QLineEdit()
        self.promotion = QLineEdit()
        self.extras = QLineEdit()
        self.app_account = QLineEdit()

        form.addRow("Status*", self.status)
        form.addRow("Provider*", self.provider)
        form.addRow("Client ID*", self.client_id)
        form.addRow("Trip ID*", self.trip_id)

        form.addRow("Booking date (YYYY-MM-DD)", self.booking_date)
        form.addRow("Travel start (YYYY-MM-DD)", self.travel_start)
        form.addRow("Travel end (YYYY-MM-DD)", self.travel_end)

        form.addRow("Destination", self.destination)
        form.addRow("Concept", self.concept)
        form.addRow("Hotel", self.hotel)
        form.addRow("Room type", self.room_type)
        form.addRow("Adults", self.adults)
        form.addRow("Children", self.children_edit)

        form.addRow("Confirmation #", self.confirmation_number)
        form.addRow("Total amount", self.total_amount)
        form.addRow("Client payments", self.client_payments)
        form.addRow("Balance amount", self.balance_amount)
        form.addRow("Payment deadline (YYYY-MM-DD)", self.payment_deadline)

        form.addRow("Park days", self.park_days)
        form.addRow("Ticket type", self.ticket_type)

        form.addRow("Photos", self.photos)
        form.addRow("Express passes", self.express_passes)
        form.addRow("Meal plan", self.meal_plan)
        form.addRow("Promotion", self.promotion)
        form.addRow("Extras", self.extras)
        form.addRow("App account", self.app_account)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.create_sale)
        right.addWidget(self.btn_save)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_form)
        right.addWidget(self.btn_clear)

        right.addStretch(1)

        self.refresh()

    def clear_form(self) -> None:
        self.status.setCurrentIndex(0)
        self.provider.setCurrentIndex(0)
        self.client_id.clear()
        self.trip_id.clear()
        self.travel_start.clear()
        self.travel_end.clear()
        self.confirmation_number.clear()
        self.total_amount.clear()
        self.booking_date.clear()
        self.destination.clear()
        self.concept.clear()
        self.hotel.clear()
        self.room_type.clear()
        self.adults.clear()
        self.children_edit.clear()
        self.client_payments.clear()
        self.balance_amount.clear()
        self.payment_deadline.clear()
        self.park_days.clear()
        self.ticket_type.clear()
        self.photos.clear()
        self.express_passes.clear()
        self.meal_plan.clear()
        self.promotion.clear()
        self.extras.clear()
        self.app_account.clear()

    def refresh(self) -> None:
        try:
            with get_session() as session:
                repo = SaleRepository(session)
                sales = repo.list(limit=200)

            self.table.setRowCount(0)
            for s in sales:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(str(s.id)))
                self.table.setItem(
                    r, 1, QTableWidgetItem(str(s.status) if s.status is not None else "")
                )
                self.table.setItem(r, 2, QTableWidgetItem(str(s.client_id)))
                self.table.setItem(r, 3, QTableWidgetItem(str(s.trip_id)))
                self.table.setItem(
                    r, 4, QTableWidgetItem(str(s.provider) if s.provider is not None else "")
                )

                self.table.setItem(r, 5, QTableWidgetItem(str(s.booking_date or "")))
                self.table.setItem(r, 6, QTableWidgetItem(str(s.travel_start_date or "")))
                self.table.setItem(r, 7, QTableWidgetItem(str(s.travel_end_date or "")))

                self.table.setItem(r, 8, QTableWidgetItem(s.destination or ""))
                self.table.setItem(r, 9, QTableWidgetItem(s.concept or ""))
                self.table.setItem(r, 10, QTableWidgetItem(s.hotel or ""))
                self.table.setItem(r, 11, QTableWidgetItem(s.room_type or ""))

                self.table.setItem(
                    r, 12, QTableWidgetItem("" if s.adults is None else str(s.adults))
                )
                self.table.setItem(r, 13, QTableWidgetItem(s.children or ""))

                self.table.setItem(r, 14, QTableWidgetItem(s.confirmation_number or ""))

                self.table.setItem(r, 15, QTableWidgetItem(str(s.total_amount or "")))
                self.table.setItem(r, 16, QTableWidgetItem(str(s.client_payments or "")))
                self.table.setItem(r, 17, QTableWidgetItem(str(s.balance_amount or "")))

                self.table.setItem(r, 18, QTableWidgetItem(str(s.payment_deadline or "")))

                self.table.setItem(
                    r, 19, QTableWidgetItem("" if s.park_days is None else str(s.park_days))
                )
                self.table.setItem(r, 20, QTableWidgetItem(s.ticket_type or ""))

                self.table.setItem(r, 21, QTableWidgetItem(s.photos or ""))
                self.table.setItem(r, 22, QTableWidgetItem(s.express_passes or ""))
                self.table.setItem(r, 23, QTableWidgetItem(s.meal_plan or ""))

                self.table.setItem(r, 24, QTableWidgetItem(s.promotion or ""))
                self.table.setItem(r, 25, QTableWidgetItem(s.extras or ""))
                self.table.setItem(r, 26, QTableWidgetItem(s.app_account or ""))

            self.log(f"Sales refreshed: {len(sales)}")
        except Exception as e:
            self.log(f"ERROR refreshing sales: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh sales:\n{e}")

    def create_sale(self) -> None:
        status = self.status.currentText()
        provider = self.provider.currentText()
        client_id_raw = self.client_id.text().strip()
        trip_id_raw = self.trip_id.text().strip()

        if not client_id_raw or not trip_id_raw:
            QMessageBox.warning(self, "Validation", "Client ID and Trip ID are required.")
            return

        try:
            client_id = int(client_id_raw)
            trip_id = int(trip_id_raw)
        except ValueError:
            QMessageBox.warning(self, "Validation", "Client ID and Trip ID must be integers.")
            return

        conf = self.confirmation_number.text().strip() or None

        try:
            booking = self._parse_iso_date(self.booking_date.text())
            travel_start = self._parse_iso_date(self.travel_start.text())
            travel_end = self._parse_iso_date(self.travel_end.text())

            total = self._parse_decimal(self.total_amount.text(), field_name="Total amount")
            client_pay = self._parse_decimal(
                self.client_payments.text(), field_name="Client payments"
            )
            balance = self._parse_decimal(self.balance_amount.text(), field_name="Balance amount")

            deadline = self._parse_iso_date(self.payment_deadline.text())

            adults = self._parse_int(self.adults.text(), field_name="Adults")
            park_days = self._parse_int(self.park_days.text(), field_name="Park days")
        except ValueError as ve:
            QMessageBox.warning(self, "Validation", str(ve))
            return

        try:
            with get_session() as session:
                repo = SaleRepository(session)
                repo.create(
                    status=status,
                    client_id=client_id,
                    trip_id=trip_id,
                    provider=provider,
                    booking_date=booking,
                    travel_start_date=travel_start,
                    travel_end_date=travel_end,
                    destination=self.destination.text().strip() or None,
                    concept=self.concept.text().strip() or None,
                    hotel=self.hotel.text().strip() or None,
                    room_type=self.room_type.text().strip() or None,
                    adults=adults,
                    children=self.children_edit.text().strip() or None,
                    confirmation_number=conf,
                    total_amount=total,
                    client_payments=client_pay,
                    balance_amount=balance,
                    payment_deadline=deadline,
                    park_days=park_days,
                    ticket_type=self.ticket_type.text().strip() or None,
                    photos=self.photos.text().strip() or None,
                    express_passes=self.express_passes.text().strip() or None,
                    meal_plan=self.meal_plan.text().strip() or None,
                    promotion=self.promotion.text().strip() or None,
                    extras=self.extras.text().strip() or None,
                    app_account=self.app_account.text().strip() or None,
                )

            self.log(f"Created sale: trip_id={trip_id}, provider={provider}")
            self.clear_form()
            self.refresh()
        except Exception as e:
            self.log(f"ERROR creating sale: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create sale:\n{e}")

    def _parse_iso_date(self, s: str) -> date | None:
        s = s.strip()
        if not s:
            return None
        return date.fromisoformat(s)  # YYYY-MM-DD

    def _parse_int(self, s: str, *, field_name: str) -> int | None:
        s = s.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError as e:
            raise ValueError(f"{field_name} must be an integer.") from e

    def _parse_decimal(self, s: str, *, field_name: str = "Value") -> Decimal | None:
        s = s.strip()
        if not s:
            return None
        try:
            return Decimal(s)
        except InvalidOperation as e:
            raise ValueError(f"{field_name} must be a valid number (e.g., 1234.56).") from e
