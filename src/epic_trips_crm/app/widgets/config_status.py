from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from epic_trips_crm.config.settings import settings


class ConfigStatus(QWidget):
    """
    What it does:
    - Displays whether required runtime config is present.

    Why it matters:
    - Prevents confusing UX failures by showing missing env vars up front.

    Behavior:
    - Shows green-ish check / red-ish missing via text (no styling yet).
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        db_ok = bool(getattr(settings, "database_url", None))
        portal_ok = all(
            [
                bool(getattr(settings, "portal_url", None)),
                bool(getattr(settings, "portal_username", None)),
                bool(getattr(settings, "portal_password", None)),
            ]
        )

        layout.addWidget(QLabel(f"DATABASE_URL: {'✅' if db_ok else '❌'}"))
        layout.addWidget(QLabel(f"Portal creds: {'✅' if portal_ok else '❌'}"))
        layout.addStretch(1)
