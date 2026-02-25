from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import Boolean, Date, Integer, Numeric

from epic_trips_crm.db.engine import get_session
from epic_trips_crm.db.models import Checklist
from epic_trips_crm.db.repositories.checklist import ChecklistRepository


class ChecklistsTab(QWidget):
    """
    What it does:
    - Gets/creates a checklist for a trip_id and lets you edit ALL checklist fields.

    Why it matters:
    - Checklist is operational tracking; later it drives portal workflow readiness.

    Behavior:
    - "Get/Create" loads a checklist row for trip_id (creates if absent).
    - "Save" updates all editable fields present in the UI (derived from the Checklist model).
    """

    def __init__(self, *, log_fn) -> None:
        super().__init__()
        self.log = log_fn
        self._current_trip_id: int | None = None
        self._current_checklist_id: int | None = None

        # field_name -> widget
        self._widgets: dict[str, QLineEdit | QCheckBox] = {}
        # field_name -> sqlalchemy column (for type-aware parsing)
        self._columns: dict[str, Any] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # LEFT: controls
        left = QVBoxLayout()
        root.addLayout(left, stretch=4)
        left.addWidget(QLabel("Checklist (by Trip ID)"))

        controls = QHBoxLayout()
        left.addLayout(controls)

        self.trip_id = QLineEdit()
        self.trip_id.setPlaceholderText("Trip ID")
        controls.addWidget(self.trip_id)

        self.btn_get = QPushButton("Get/Create")
        self.btn_get.clicked.connect(self.get_or_create)
        controls.addWidget(self.btn_get)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_form)
        controls.addWidget(self.btn_clear)

        controls.addStretch(1)

        left.addStretch(1)

        # RIGHT: scrollable form (so “all fields” remains usable)
        right = QVBoxLayout()
        root.addLayout(right, stretch=6)

        right.addWidget(QLabel("Checklist fields"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        right.addWidget(scroll, stretch=1)

        scroll_body = QWidget()
        scroll.setWidget(scroll_body)

        scroll_layout = QVBoxLayout(scroll_body)
        form = QFormLayout()
        scroll_layout.addLayout(form)
        scroll_layout.addStretch(1)

        # Build widgets dynamically from the model columns
        for col in Checklist.__table__.columns:
            name = col.name

            # Skip primary/foreign keys from editing (still used implicitly via trip_id)
            if name in ("id", "trip_id"):
                continue

            label = name.replace("_", " ").title()

            if isinstance(col.type, Boolean):
                w = QCheckBox()
                form.addRow(label, w)
            else:
                w = QLineEdit()
                if isinstance(col.type, Date):
                    w.setPlaceholderText("YYYY-MM-DD")
                elif isinstance(col.type, Integer):
                    w.setPlaceholderText("Integer")
                elif isinstance(col.type, Numeric):
                    w.setPlaceholderText("Decimal (e.g. 1234.56)")
                form.addRow(label, w)

            self._widgets[name] = w
            self._columns[name] = col

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save)
        right.addWidget(self.btn_save)

    def clear_form(self) -> None:
        self._current_trip_id = None
        self._current_checklist_id = None
        self.trip_id.clear()

        for w in self._widgets.values():
            if isinstance(w, QCheckBox):
                w.setChecked(False)
            else:
                w.clear()

    def get_or_create(self) -> None:
        trip_id_raw = self.trip_id.text().strip()
        if not trip_id_raw:
            QMessageBox.warning(self, "Validation", "Trip ID is required.")
            return

        try:
            trip_id = int(trip_id_raw)
        except ValueError:
            QMessageBox.warning(self, "Validation", "Trip ID must be an integer.")
            return

        try:
            with get_session() as session:
                repo = ChecklistRepository(session)
                checklist = repo.get_or_create_by_trip_id(trip_id)

            self._current_trip_id = trip_id
            self._current_checklist_id = checklist.id  # IMPORTANT: real checklist id

            # Populate UI from model
            for field, w in self._widgets.items():
                val = getattr(checklist, field, None)
                if isinstance(w, QCheckBox):
                    w.setChecked(bool(val))
                else:
                    w.setText("" if val is None else str(val))

            self.log(
                f"Checklist loaded: trip_id={trip_id}, checklist_id={self._current_checklist_id}"
            )
        except Exception as e:
            self.log(f"ERROR loading checklist: {e}")
            QMessageBox.critical(self, "Error", f"Failed to get/create checklist:\n{e}")

    def save(self) -> None:
        if not self._current_trip_id:
            QMessageBox.warning(self, "Validation", "Load a checklist first (Get/Create).")
            return

        # Collect and parse fields based on SQLAlchemy column types
        fields: dict[str, Any] = {}
        try:
            for field, w in self._widgets.items():
                col = self._columns[field]

                if isinstance(w, QCheckBox):
                    fields[field] = w.isChecked()
                    continue

                txt = w.text().strip()
                if txt == "":
                    fields[field] = None
                    continue

                if isinstance(col.type, Date):
                    fields[field] = self._parse_iso_date(txt, field_name=field)
                elif isinstance(col.type, Integer):
                    fields[field] = self._parse_int(txt, field_name=field)
                elif isinstance(col.type, Numeric):
                    fields[field] = self._parse_decimal(txt, field_name=field)
                else:
                    fields[field] = txt

        except ValueError as ve:
            QMessageBox.warning(self, "Validation", str(ve))
            return

        try:
            with get_session() as session:
                repo = ChecklistRepository(session)
                repo.update_by_trip_id(self._current_trip_id, **fields)

            self.log(f"Checklist updated: checklist_id={self._current_checklist_id}")
        except Exception as e:
            self.log(f"ERROR saving checklist: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save checklist:\n{e}")

    def _parse_iso_date(self, s: str, *, field_name: str) -> date:
        try:
            return date.fromisoformat(s)
        except ValueError as e:
            raise ValueError(f"{field_name} must be a date in YYYY-MM-DD format.") from e

    def _parse_int(self, s: str, *, field_name: str) -> int:
        try:
            return int(s)
        except ValueError as e:
            raise ValueError(f"{field_name} must be an integer.") from e

    def _parse_decimal(self, s: str, *, field_name: str) -> Decimal:
        try:
            return Decimal(s)
        except InvalidOperation as e:
            raise ValueError(f"{field_name} must be a valid number (e.g., 1234.56).") from e
