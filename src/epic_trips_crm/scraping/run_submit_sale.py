from __future__ import annotations

import argparse
import json
from pathlib import Path

from epic_trips_crm.config.settings import settings
from epic_trips_crm.db.engine import get_session
from epic_trips_crm.scraping.travelagentportal_playwright import PlaywrightPortalClient
from epic_trips_crm.services.portal_client import PortalCredentials
from epic_trips_crm.services.sales_submission import SalesSubmissionService


def _require_portal_settings() -> None:
    missing = []
    if not settings.portal_url:
        missing.append("PORTAL_URL")
    if not settings.portal_username:
        missing.append("PORTAL_USERNAME")
    if not settings.portal_password:
        missing.append("PORTAL_PASSWORD")
    if missing:
        raise RuntimeError(f"Missing required portal settings: {', '.join(missing)}")


def _load_json_file(path: str | None) -> dict | list:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"JSON file not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    """
    What it does:
    - Provides two run modes:
        1) submit-sale: DB-driven submission flow (still NO final submit in portal client)
        2) portal-existing-form: portal-only edit of an existing form (no DB required)
        3) portal-final-submit: DANGEROUS final submit of an existing form (no DB required, IRREVERSIBLE)

    Why it matters:
    - Lets you debug portal automation without touching Neon.
    - Keeps a single entrypoint for local development.

    Behavior:
    - Always uses PlaywrightPortalClient which hard-blocks final submit.
    - In portal-existing-form:
        - opens existing form id
        - adds optional traveler/components from JSON files
        - exits
    """
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- DB-driven mode ---
    p_submit = sub.add_parser("submit-sale", help="DB-driven: load sale from Neon and run portal flow (NO final submit).")
    p_submit.add_argument("--sale-id", type=int, required=True)
    p_submit.add_argument("--headful", action="store_true", help="Show the browser window for debugging.")

    # --- Portal-only mode ---
    p_portal = sub.add_parser("portal-existing-form", help="Portal-only: open an existing form and add traveler/components (NO DB).")
    p_portal.add_argument("--form-id", type=str, default="EVO2026153349")
    p_portal.add_argument("--traveler-json", type=str, default=None, help="Path to traveler JSON dict.")
    p_portal.add_argument("--components-json", type=str, default=None, help="Path to components JSON list.")
    p_portal.add_argument("--headful", action="store_true", help="Show the browser window for debugging.")

    # --- Portal-final-submit mode ---
    p_final = sub.add_parser(
        "portal-final-submit",
        help="DANGEROUS: Final-submit an existing form in the portal (irreversible)."
    )
    p_final.add_argument("--form-id", type=str, required=True)
    p_final.add_argument("--headful", action="store_true", help="Show the browser window for debugging.")
    p_final.add_argument(
        "--i-understand-this-will-submit",
        action="store_true",
        help="Required safety flag. Without this, the command refuses to run."
    )

    args = parser.parse_args()
    _require_portal_settings()

    portal_url = settings.portal_url
    if not portal_url:
        raise RuntimeError("PORTAL_URL is missing")

    portal = PlaywrightPortalClient(
        base_url=portal_url,
        headless=not getattr(args, "headful", False),
        default_form_id="EVO2026153349",
    )

    creds = PortalCredentials(
        username=settings.portal_username or "",
        password=settings.portal_password or "",
    )

    try:
        portal.login(creds)

        if args.cmd == "portal-existing-form":
            traveler = _load_json_file(args.traveler_json) if args.traveler_json else None
            components = _load_json_file(args.components_json) if args.components_json else []
            if components and not isinstance(components, list):
                raise RuntimeError("--components-json must be a JSON list of component dicts.")

            payload = {
                "existing_form_id": args.form_id,
                "client_data": traveler if traveler else None,
                "components": components,
            }

            result = portal.submit_sale(payload)
            print(f"OK: portal-only existing form updated, confirmation_id={result.confirmation_id}")
            return

        if args.cmd == "submit-sale":
            # DB-driven flow (still safe: portal client will never final submit)
            service = SalesSubmissionService(portal=portal)
            with get_session() as session:
                outcome = service.submit_sale(session=session, sale_id=args.sale_id, creds=creds)
                print(f"OK: sale_id={outcome.sale_id} confirmation_id={outcome.confirmation_id}")
            return
        
        if args.cmd == "portal-final-submit":
            if not args.i_understand_this_will_submit:
                raise RuntimeError(
                    "Refusing to final-submit without --i-understand-this-will-submit"
                )

            result = portal.final_submit_existing_form(args.form_id)
            print(f"OK: final-submitted form_id={args.form_id} confirmation_id={result.confirmation_id}")
            return

    finally:
        portal.close()


if __name__ == "__main__":
    main()
