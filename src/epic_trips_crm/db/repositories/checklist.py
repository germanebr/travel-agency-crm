from __future__ import annotations

from sqlalchemy import select

from epic_trips_crm.db.models import Checklist
from epic_trips_crm.db.repositories.base import BaseRepository
from epic_trips_crm.utils.errors import NotFoundError


class ChecklistRepository(BaseRepository):
    def create_for_trip(self, trip_id: int) -> Checklist:
        """
        What it does:
        - Creates a checklist linked to a trip (checklist.trip_id).

        Why it matters:
        - Ensures each trip can have a single checklist record (DB unique constraint on trip_id).

        Behavior:
        - Inserts a new row, flushes so checklist.id is generated immediately.
        - If a checklist already exists for the trip, the DB will raise a uniqueness error.
        """
        checklist = Checklist(trip_id=trip_id)
        self.session.add(checklist)
        self.session.flush()
        return checklist

    def get(self, checklist_id: int) -> Checklist:
        """
        What it does:
        - Fetches a checklist by primary key.

        Why it matters:
        - Checklist detail view or debugging.

        Behavior:
        - Raises NotFoundError if missing.
        """
        checklist = self.session.get(Checklist, checklist_id)
        if not checklist:
            raise NotFoundError(f"Checklist {checklist_id} not found")
        return checklist

    def get_by_trip_id(self, trip_id: int) -> Checklist | None:
        """
        What it does:
        - Fetches the checklist for a trip.

        Why it matters:
        - This is the most common access pattern for your UI (Trip -> Checklist).

        Behavior:
        - Returns None if the trip has no checklist yet.
        """
        stmt = select(Checklist).where(Checklist.trip_id == trip_id)
        return self.session.scalars(stmt).first()

    def get_or_create_by_trip_id(self, trip_id: int) -> Checklist:
        """
        What it does:
        - Returns the checklist for a trip, creating it if missing.

        Why it matters:
        - Lets your UI assume a checklist exists without requiring a separate 'create checklist' action.

        Behavior:
        - If checklist exists -> returns it.
        - If not -> inserts a new checklist row and flushes.
        """
        existing = self.get_by_trip_id(trip_id)
        if existing:
            return existing
        return self.create_for_trip(trip_id)

    def update_by_trip_id(self, trip_id: int, **fields) -> Checklist:
        """
        What it does:
        - Updates checklist fields (booleans, dates, notes) for a given trip.

        Why it matters:
        - Your UI will toggle flags frequently; this provides one safe update method.

        Behavior:
        - Ensures a checklist exists (creates one if missing).
        - Only updates attributes that exist on the model.
        - Flushes changes so they're persisted at commit.
        """
        checklist = self.get_or_create_by_trip_id(trip_id)

        for k, v in fields.items():
            if hasattr(checklist, k):
                setattr(checklist, k, v)

        self.session.flush()
        return checklist

    def delete(self, checklist_id: int) -> None:
        """
        What it does:
        - Deletes a checklist record.

        Why it matters:
        - Cleanup/testing.

        Behavior:
        - Deletes and flushes.
        - If Trip references checklist via trips.checklist_id, DB constraints may block deletion.
        """
        checklist = self.get(checklist_id)
        self.session.delete(checklist)
        self.session.flush()
