from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from epic_trips_crm.db.models import Commission
from epic_trips_crm.db.repositories.base import BaseRepository
from epic_trips_crm.utils.errors import NotFoundError


class CommissionRepository(BaseRepository):
    def create(
        self,
        *,
        sale_id: int,
        commission_form_ref: str | None = None,
        estimated_commission: Decimal | None = None,
        thirty_day_date: date | None = None,
        commission_due_date: date | None = None,
        commission_received: Decimal | None = None,
    ) -> Commission:
        """
        What it does:
        - Inserts a Commission row linked to a Sale via sale_id.

        Why it matters:
        - A commission record is where you'll store the portal confirmation reference
          and track expected vs received payouts.

        Behavior:
        - Adds the object to the session and flushes so commission.id is available immediately.
        - DB enforces one-to-one with Sale because commissions.sale_id is UNIQUE.
        """
        commission = Commission(
            sale_id=sale_id,
            commission_form_ref=commission_form_ref,
            estimated_commission=estimated_commission,
            thirty_day_date=thirty_day_date,
            commission_due_date=commission_due_date,
            commission_received=commission_received,
        )
        self.session.add(commission)
        self.session.flush()
        return commission

    def get(
        self,
        commission_id: int,
        *,
        include_sale: bool = False,
    ) -> Commission:
        """
        What it does:
        - Fetches a Commission by primary key.

        Why it matters:
        - Commission detail view and edit workflows.

        Behavior:
        - Optional eager-load of the related Sale to avoid lazy-loading after session closes.
        """
        if not include_sale:
            commission = self.session.get(Commission, commission_id)
            if not commission:
                raise NotFoundError(f"Commission {commission_id} not found")
            return commission

        stmt = (
            select(Commission)
            .where(Commission.id == commission_id)
            .options(selectinload(Commission.sale))
        )
        commission = self.session.scalars(stmt).first()
        if not commission:
            raise NotFoundError(f"Commission {commission_id} not found")
        return commission

    def get_by_sale_id(self, sale_id: int, *, include_sale: bool = False) -> Commission | None:
        """
        What it does:
        - Fetches the commission row for a given sale_id (one-to-one).

        Why it matters:
        - Scraper workflow: given a sale, update its commission ref/status.

        Behavior:
        - Returns None if missing (useful if you create commissions lazily).
        """
        stmt = select(Commission).where(Commission.sale_id == sale_id)
        if include_sale:
            stmt = stmt.options(selectinload(Commission.sale))
        return self.session.scalars(stmt).first()

    def list_missing_form_ref(self, *, limit: int = 200) -> list[Commission]:
        """
        What it does:
        - Lists commissions that don't yet have a portal confirmation reference.

        Why it matters:
        - This becomes your "to submit" queue for the sales portal automation.

        Behavior:
        - Treats NULL or empty string as missing.
        """
        stmt = (
            select(Commission)
            .where(
                (Commission.commission_form_ref.is_(None)) | (Commission.commission_form_ref == "")
            )
            .order_by(Commission.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_due_within(
        self, days: int, *, from_date: date | None = None, limit: int = 200
    ) -> list[Commission]:
        """
        What it does:
        - Lists commissions with commission_due_date within the next `days`.

        Why it matters:
        - Lets you proactively track expected payouts.

        Behavior:
        - Only considers rows where commission_due_date is not NULL.
        - Filters in SQL using date comparisons.
        """
        start = from_date or date.today()
        end = start + timedelta(days=days)

        stmt = (
            select(Commission)
            .where(Commission.commission_due_date.is_not(None))
            .where(Commission.commission_due_date >= start)
            .where(Commission.commission_due_date <= end)
            .order_by(Commission.commission_due_date.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def set_form_ref(self, sale_id: int, form_ref: str) -> Commission:
        """
        What it does:
        - Sets commission_form_ref for a given sale_id.

        Why it matters:
        - This is the exact method your scraper will call after submitting the sale
          and receiving the confirmation ID from the portal.

        Behavior:
        - Raises NotFoundError if the commission row doesn't exist.
        - Flushes so the update is persisted at commit.
        """
        commission = self.get_by_sale_id(sale_id)
        if not commission:
            raise NotFoundError(f"Commission for sale_id={sale_id} not found")

        commission.commission_form_ref = form_ref
        self.session.flush()
        return commission

    def mark_received(self, commission_id: int, amount: Decimal) -> Commission:
        """
        What it does:
        - Sets commission_received to a specific amount.

        Why it matters:
        - You’ll want to record real payouts and later compute deltas.

        Behavior:
        - Flushes so change is stored on commit.
        """
        commission = self.get(commission_id)
        commission.commission_received = amount
        self.session.flush()
        return commission

    def delete(self, commission_id: int) -> None:
        """
        What it does:
        - Deletes a commission record.

        Why it matters:
        - Cleanup/testing; in production you may prefer audit trails.

        Behavior:
        - Deletes the row and flushes.
        """
        commission = self.get(commission_id)
        self.session.delete(commission)
        self.session.flush()
