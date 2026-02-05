from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from epic_trips_crm.db.base import Base

SCHEMA = "epic_trips_crm"

# These enums already exist in Postgres. We reference them without creating types.
trip_status_enum = ENUM("trip_status", schema=SCHEMA, create_type=False)
sale_status_enum = ENUM("sale_status", schema=SCHEMA, create_type=False)
provider_name_enum = ENUM("provider_name", schema=SCHEMA, create_type=False)


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trips: Mapped[list[Trip]] = relationship(back_populates="client")
    sales: Mapped[list[Sale]] = relationship(back_populates="client")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    trip_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(trip_status_enum, nullable=False)

    client_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.clients.id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )

    start_month: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    end_month: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    companions: Mapped[str | None] = mapped_column(Text, nullable=True)
    flights: Mapped[str | None] = mapped_column(Text, nullable=True)

    reservation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    checklist_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.checklist.id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=True,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship(back_populates="trips")
    sales: Mapped[list[Sale]] = relationship(back_populates="trip")

    # One-to-one (optional) link via trips.checklist_id
    checklist_via_checklist_id: Mapped[Checklist | None] = relationship(
        "Checklist",
        foreign_keys=[checklist_id],
        uselist=False,
        post_update=True,  # helps with circular FK patterns
    )


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    status: Mapped[str] = mapped_column(sale_status_enum, nullable=False)

    client_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.clients.id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )
    trip_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.trips.id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=False,
        index=True,
    )

    booking_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    travel_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    travel_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    provider: Mapped[str] = mapped_column(provider_name_enum, nullable=False)

    destination: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotel: Mapped[str | None] = mapped_column(Text, nullable=True)
    room_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    adults: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    children: Mapped[str | None] = mapped_column(Text, nullable=True)

    confirmation_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    client_payments: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    payment_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    park_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ticket_type: Mapped[str | None] = mapped_column(Text, nullable=True)

    photos: Mapped[str | None] = mapped_column(Text, nullable=True)
    express_passes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meal_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    promotion: Mapped[str | None] = mapped_column(Text, nullable=True)
    extras: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_account: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    client: Mapped[Client] = relationship(back_populates="sales")
    trip: Mapped[Trip] = relationship(back_populates="sales")

    commission: Mapped[Commission | None] = relationship(
        back_populates="sale", uselist=False, cascade="all, delete-orphan"
    )


class Commission(Base):
    __tablename__ = "commissions"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    sale_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.sales.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=False,
        unique=True,
        index=True,
    )

    commission_form_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_commission: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    thirty_day_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    commission_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    commission_received: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sale: Mapped[Sale] = relationship(back_populates="commission")


class Checklist(Base):
    __tablename__ = "checklist"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{SCHEMA}.trips.id", ondelete="CASCADE", onupdate="NO ACTION"),
        nullable=True,
        unique=True,
        index=True,
    )

    activities_restaurants: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reservations_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    form_sent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    parks_reserved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    session_scheduled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_session_done: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lightning_lanes_planned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lightning_lanes_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    itinerary_adjusted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    videos_sent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    guides_sent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_session_scheduled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_session_done_2: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    final_confirmation_done: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photos_received: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    review_received: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # One-to-one (optional) link via checklist.trip_id
    trip: Mapped[Trip | None] = relationship(
        "Trip",
        foreign_keys=[trip_id],
        uselist=False,
        post_update=True,  # helps with circular FK patterns
    )
