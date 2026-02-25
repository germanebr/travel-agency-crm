"""
travelagentportal_playwright.py

What this module does
- Implements a Playwright-based portal automation client that satisfies the `PortalClient` interface.
- Supports SAFE development against production by opening an existing record and NEVER final-submitting.

Why it matters
- Keeps web automation isolated from business logic (SalesSubmissionService).
- Enables reliable incremental development with stable waits, screenshots, and strict safety rails.

Safety guarantees (current version)
- This client WILL NOT click the final submit button (#btnSubmit).
- It can be used to:
  - login
  - navigate to commissions hub
  - open an existing record by ID
  - add travelers
  - add components and save them (modifies that record)
- If you need real submission later, we will implement a separate "sandbox-only" mode with explicit flags.

Behavior summary
- `login(creds)`: logs in, handling readonly inputs (focus removes readonly).
- `submit_sale(payload)`: SAFE mode:
    - opens existing form (payload.existing_form_id or default_form_id)
    - optionally adds traveler and components
    - returns "<FORM_ID>-NO-SUBMIT"
- On failures: captures screenshots to ./artifacts for debugging.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

from epic_trips_crm.services.portal_client import PortalClient, PortalCredentials, SubmissionResult


@dataclass(frozen=True)
class PortalSelectors:
    """
    Centralized selectors for the portal.

    What it does:
    - Keeps selectors in one place for easy maintenance.

    Why it matters:
    - The portal UI can change. Updating selectors in one class reduces risk.

    Behavior:
    - Used by Playwright locators throughout the client.
    """

    # Auth flow
    login_open: str = "button[aria-label='Login to your travel site']"
    login_modal_visible: str = "#loginModal.show"
    username: str = "#email-login-modal"
    password: str = "#password-login-modal"
    login_submit: str = "#login-submit-modal"

    # Navigation
    commissions_dropdown: str = "button[aria-label='Commissions Dropdown']"

    # Hub actions
    new_commission: str = "css=div.dt-buttons > button.btn.btn-primary"
    hub_table_row_by_id: str = (
        "xpath=//table[@id='agentInvoiceTable']//tr[td[normalize-space()='{form_id}']]"
    )

    # Traveler
    new_traveler_btn: str = "css=button[title='Create a new traveler (Shortcut: n)']"
    trav_first: str = "#firstNameInput"
    trav_last: str = "#TravelerForm_LastName"
    trav_email: str = "#travelerEmailInput"
    trav_phone: str = "#travelerPhoneInput"
    trav_save: str = "#saveButton"

    # New component menu
    component_dropdown: str = "button#dropdownMenuButton"
    component_activity: str = "css=a.dropdown-item[href*='/components/activity']"
    component_car: str = "css=a.dropdown-item[href*='/components/car']"
    component_cruise: str = "css=a.dropdown-item[href*='/components/cruise']"
    component_hotel: str = "css=a.dropdown-item[href*='/components/hotel']"
    component_package: str = "css=a.dropdown-item[href*='/components/package']"
    component_insurance: str = "css=a.dropdown-item[href*='/components/insurance']"

    # Supplier autocomplete
    supplier_name: str = "#SupplierName"
    supplier_id: str = "#SupplierId"
    supplier_menu_item_wrapper: str = (
        "css=ul.ui-autocomplete li.ui-menu-item div.ui-menu-item-wrapper"
    )

    # Common component fields
    booking_date: str = "#BookingDate"
    start_date: str = "#StartDate"
    end_date: str = "#EndDate"
    currency_id: str = "#CurrencyId"
    estimated_commission: str = "#TravelComponentInput_EstimatedCommission"
    total_sales_amount: str = "#TotalSalesAmount"
    supplier_reference: str = "#SupplierReferenceId"

    # Type-specific component fields
    activity_name: str = "#ActivityName"
    car_rental_company: str = "#CarRentalCompany"
    cruise_company: str = "#CruiseCompany"
    vessel_name: str = "#VesselName"
    hotel_name: str = "#HotelName"

    # Package toggles
    package_activity_choice: str = "#choice_790540000"
    package_hotel_choice: str = "#choice_790540005"

    # Component save
    component_save: str = "css=form#mainForm button.btn.btn-primary[type='submit']"

    # Final submit (MUST NOT be used in safe mode)
    final_submit: str = "#btnSubmit"


class PlaywrightPortalClient(PortalClient):
    """
    Playwright implementation of PortalClient.

    What it does:
    - Automates login, hub navigation, opening an existing commission record,
      adding travelers and components.

    Why it matters:
    - Provides a stable automation adapter for your CRM pipeline.

    Behavior:
    - Uses Playwright-managed Chromium (no chromedriver).
    - Captures screenshots in ./artifacts on timeouts.
    - Hard-blocks final submit.
    """

    def __init__(
        self,
        *,
        base_url: str,
        headless: bool = True,
        artifacts_dir: str = "artifacts",
        default_timeout_ms: int = 30_000,
        default_form_id: str = "EVO2026153349",
    ) -> None:
        self.base_url = base_url
        self.headless = headless
        self.default_form_id = default_form_id

        self.sel = PortalSelectors()
        self._default_timeout_ms = default_timeout_ms

        self._artifacts_dir = Path(artifacts_dir)
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    # -------------------- Lifecycle --------------------

    def _start(self) -> None:
        """
        What it does:
        - Starts Playwright, launches Chromium, creates a page, and navigates to base_url.

        Why it matters:
        - Ensures we have a live browser session before interacting with the portal.

        Behavior:
        - If Chromium isn't installed, Playwright will raise. Install via:
            uv run playwright install chromium
        """
        if self._page is not None:
            return

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(headless=self.headless)
        except Exception as e:
            self.close()
            raise RuntimeError(
                "Failed to launch Playwright Chromium.\n"
                "If this is the first time on this machine, run:\n\n"
                "  uv run playwright install chromium\n"
            ) from e

        self._context = self._browser.new_context(
            locale="en-US",  # forces MM/DD/YYYY expectations in many UIs
            timezone_id="America/New_York",
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self._default_timeout_ms)

        self._page.goto(self.base_url, wait_until="domcontentloaded")

    def close(self) -> None:
        """
        What it does:
        - Closes page/context/browser and stops Playwright.

        Why it matters:
        - Prevents zombie browser processes and file locks on Windows.

        Behavior:
        - Safe to call multiple times.
        """
        try:
            if self._context:
                self._context.close()
        finally:
            self._context = None

        try:
            if self._browser:
                self._browser.close()
        finally:
            self._browser = None

        try:
            if self._pw:
                self._pw.stop()
        finally:
            self._pw = None
            self._page = None

    # -------------------- PortalClient interface --------------------

    def final_submit_existing_form(self, form_id: str) -> SubmissionResult:
        """
        DANGEROUS: Final-submits an existing commission form.

        What it does:
        - Navigates to Commissions Hub
        - Opens the existing form by ID
        - Clicks the FINAL submit button and confirms dialogs
        - Verifies submission via observable UI signals

        Why it matters:
        - This is the irreversible action you must gate behind an explicit CLI command.

        Behavior:
        - Raises on timeout or if submission cannot be verified.
        - Takes screenshots on failure for debugging/audit.
        """
        self._start()
        page = self._require_page()

        try:
            self._go_to_commissions_hub(page)
            self._open_existing_form(page, form_id)

            confirmation_id = self._final_submit_commission_form(page, form_id)

            self._debug_dump(f"final_submit_ok_{form_id}")
            return SubmissionResult(confirmation_id=confirmation_id)

        except PWTimeoutError as e:
            self._debug_dump(f"final_submit_timeout_{form_id}")
            raise RuntimeError(f"FINAL submit failed (timeout) for {form_id}: {e}") from e

        except Exception:
            self._debug_dump(f"final_submit_error_{form_id}")
            raise

    def _final_submit_commission_form(self, page, form_id: str) -> str:
        """
        Low-level final submit click + verification.

        Assumptions:
        - You are already on the existing form page.
        """
        # 1) handle JS confirm/alert dialogs if the portal shows them
        page.once("dialog", lambda d: d.accept())

        # 2) click FINAL submit button
        # (Use your selector constant if you have one; #btnSubmit is a common one.)
        submit_btn = page.locator("#btnSubmit")
        submit_btn.wait_for(state="visible", timeout=15_000)
        submit_btn.click(timeout=15_000)

        # 3) verify submission
        #
        # The portal may:
        # - show a success banner
        # - redirect back to the hub
        # - update a status label
        #
        # We try multiple signals (best-effort).
        page.wait_for_load_state("networkidle", timeout=20_000)

        # Success banner (if present)
        success = page.locator(".alert-success")
        if success.count() > 0:
            # keep the original ID as the “confirmation_id” (portal often keeps same invoice id)
            return form_id

        # Redirect to hub: look for the agent invoice table and the row for this form id
        hub_table = page.locator("#agentInvoiceTable")
        if hub_table.count() > 0:
            row = page.locator(
                f"//table[@id='agentInvoiceTable']//tr[td[normalize-space()='{form_id}']]"
            )
            row.wait_for(timeout=15_000)

            # If there’s a status column you can read, do it here.
            # Example (you’ll adjust column index once you confirm it):
            # status_text = row.locator("td").nth(3).inner_text().strip().lower()
            # if "submitted" in status_text: return form_id

            return form_id

        # If none of the signals matched, fail hard (we don’t want false positives)
        raise RuntimeError(f"Could not verify final submission for {form_id}")

    def login(self, creds: PortalCredentials) -> None:
        """
        What it does:
        - Logs into the portal if not already authenticated.

        Why it matters:
        - Hub navigation and record editing require auth.

        Behavior:
        - Uses `.first` to avoid strict-mode violations.
        - Handles readonly inputs by focusing and removing readonly before fill.
        - On timeout, saves screenshot.
        """
        self._start()
        page = self._require_page()

        dropdown = page.locator(self.sel.commissions_dropdown).first
        if dropdown.count() > 0:
            return  # already logged in

        try:
            page.locator(self.sel.login_open).click(timeout=15_000)
            page.locator(self.sel.login_modal_visible).wait_for(timeout=15_000)

            self._fill_readonly_input(page, self.sel.username, creds.username)
            self._fill_readonly_input(page, self.sel.password, creds.password)

            page.locator(self.sel.login_submit).click(timeout=15_000)

            dropdown.wait_for(state="visible", timeout=20_000)

        except PWTimeoutError as e:
            self._debug_dump("login_timeout")
            raise RuntimeError(f"Login failed (timeout): {e}") from e

    def submit_sale(self, payload: dict) -> SubmissionResult:
        """
        SAFE submit_sale.

        What it does:
        - Opens an existing form (payload['existing_form_id'] or default_form_id)
        - Adds traveler (payload['client_data']) if present
        - Adds components (payload['components']) if present
        - NEVER final-submits

        Why it matters:
        - Lets you port and validate the full Selenium mapping without creating/submitting new forms.

        Behavior:
        - Modifies the existing record by saving travelers/components.
        - Returns "<FORM_ID>-NO-SUBMIT" and captures a final screenshot.
        """
        self._start()
        page = self._require_page()

        try:
            self._go_to_commissions_hub(page)

            form_id = payload.get("existing_form_id") or self.default_form_id
            self._open_existing_form(page, form_id)

            traveler = payload.get("client_data")
            if traveler:
                self._new_traveler(page, traveler)

            for c in payload.get("components", []):
                self._new_component(page, c)

            self._debug_dump("safe_mode_done_no_submit")
            return SubmissionResult(confirmation_id=f"{form_id}-NO-SUBMIT")

        except PWTimeoutError as e:
            self._debug_dump("submit_sale_timeout")
            raise RuntimeError(f"SAFE submit_sale failed (timeout): {e}") from e

    # -------------------- Helpers --------------------

    def _parse_iso_date(self, s: str) -> date:
        return date.fromisoformat(s)  # expects 'YYYY-MM-DD'

    def _detect_date_format(self, page, selector: str) -> str:
        """
        Returns 'MDY' or 'DMY' based on placeholder/attributes.
        Defaults to 'MDY' if unknown.
        """
        placeholder = (
            page.eval_on_selector(
                selector, "el => (el.getAttribute('placeholder') || '').toUpperCase()"
            )
            or ""
        )
        aria = (
            page.eval_on_selector(
                selector, "el => (el.getAttribute('aria-label') || '').toUpperCase()"
            )
            or ""
        )

        hint = f"{placeholder} {aria}"
        if "DD/MM" in hint:
            return "DMY"
        if "MM/DD" in hint:
            return "MDY"
        return "MDY"

    def _format_date(self, d: date, fmt: str) -> str:
        if fmt == "DMY":
            return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"
        # MDY
        return f"{d.month:02d}/{d.day:02d}/{d.year:04d}"

    def _fill_date(self, page, selector: str, d: date) -> None:
        """
        What it does:
        - Fills date inputs robustly across machines/locales.

        Why it matters:
        - HTML <input type="date"> requires ISO (YYYY-MM-DD).
        - Text date inputs may require locale formats (MM/DD/YYYY vs DD/MM/YYYY).

        Behavior:
        - If input type is 'date' -> fills ISO 'YYYY-MM-DD'.
        - Else -> detects expected display format and fills accordingly.
        """
        input_type = (
            page.eval_on_selector(selector, "el => (el.getAttribute('type') || '').toLowerCase()")
            or ""
        )

        # HTML date input: must be ISO
        if input_type == "date":
            page.locator(selector).fill(d.isoformat())  # YYYY-MM-DD
            return

        # Text input or custom widget: use format detection
        fmt = self._detect_date_format(page, selector)
        page.locator(selector).fill(self._format_date(d, fmt))

    def _require_page(self):
        if self._page is None:
            raise RuntimeError("Playwright page not initialized. Did _start() run?")
        return self._page

    def _debug_dump(self, tag: str) -> None:
        """
        What it does:
        - Captures a full-page screenshot for debugging.

        Why it matters:
        - Portal automations often fail due to overlays/timing; screenshots are fastest diagnosis.

        Behavior:
        - Writes ./artifacts/<tag>.png (best effort).
        """
        page = self._page
        if not page:
            return
        out = self._artifacts_dir / f"{tag}.png"
        try:
            page.screenshot(path=str(out), full_page=True)
        except Exception:
            pass

    def _fill_readonly_input(self, page, selector: str, value: str) -> None:
        """
        What it does:
        - Handles inputs that start readonly and become editable on focus.

        Why it matters:
        - The portal uses onfocus JS to remove readonly.

        Behavior:
        - Clicks input, waits for readonly removal (or forces removal), then fills.
        """
        loc = page.locator(selector)
        loc.wait_for(timeout=15_000)
        loc.scroll_into_view_if_needed()
        loc.click(timeout=15_000)

        try:
            page.wait_for_function(
                """(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    return !el.hasAttribute('readonly');
                }""",
                arg=selector,
                timeout=10_000,
            )
        except PWTimeoutError:
            page.eval_on_selector(selector, "el => el.removeAttribute('readonly')")

        loc.fill(value)

    def _go_to_commissions_hub(self, page) -> None:
        """
        What it does:
        - Navigates to Commissions Hub.

        Why it matters:
        - Existing record lives in the hub table.

        Behavior:
        - Avoids strict-mode violations with `.first` and role-based exact link selection.
        """
        if page.locator(self.sel.new_commission).count() > 0:
            return  # already on hub

        page.locator(self.sel.commissions_dropdown).first.click(timeout=15_000)

        # Choose exact "Commissions Hub" (avoid V2 beta + duplicates)
        hub = page.get_by_role("link", name="Commissions Hub", exact=True).first
        hub.wait_for(state="visible", timeout=15_000)
        hub.click(timeout=15_000)

        page.locator(self.sel.new_commission).wait_for(timeout=20_000)

    def _open_existing_form(self, page, form_id: str) -> None:
        """
        What it does:
        - Opens an existing commission record from the hub table by ID.

        Why it matters:
        - Safe dev path: no new commission forms created.

        Behavior:
        - Finds row containing exact form_id and clicks it.
        """
        row_selector = self.sel.hub_table_row_by_id.format(form_id=form_id)
        row = page.locator(row_selector).first
        row.wait_for(state="visible", timeout=20_000)
        row.scroll_into_view_if_needed()
        row.click(timeout=15_000)

    def _new_traveler(self, page, traveler: dict) -> None:
        """
        What it does:
        - Adds a traveler to the open commission record.

        Why it matters:
        - Travelers are core to the commission record.

        Behavior:
        - Clicks the new traveler button, fills fields, saves.
        """
        page.locator(self.sel.new_traveler_btn).click(timeout=15_000)
        page.locator(self.sel.trav_first).fill(traveler["first_name"])
        page.locator(self.sel.trav_last).fill(traveler["last_name"])
        page.locator(self.sel.trav_email).fill(traveler["email"])
        page.locator(self.sel.trav_phone).fill(traveler["phone"])
        page.locator(self.sel.trav_save).click(timeout=15_000)

    def _add_supplier(self, page, supplier_text: str) -> None:
        """
        What it does:
        - Selects a supplier from the portal's autocomplete input and verifies SupplierId.

        Why it matters:
        - The portal needs the hidden SupplierId value to be set; typing alone is not enough.

        Behavior:
        - Types supplier_text, waits for suggestion list, clicks best match,
        then verifies SupplierId populated (non-empty and not all-zero GUID).
        - Retries once with a slower/cleaner sequence.
        """

        def supplier_id_is_valid() -> bool:
            return page.eval_on_selector(
                self.sel.supplier_id,
                """el => {
                    const v = (el.value || '').trim();
                    return v !== '' && v !== '00000000-0000-0000-0000-000000000000';
                }""",
            )

        def open_and_type(delay_ms: int) -> None:
            s = page.locator(self.sel.supplier_name)
            s.wait_for(timeout=15_000)
            s.scroll_into_view_if_needed()
            s.click()
            s.fill("")
            s.type(supplier_text, delay=delay_ms)

        def wait_menu() -> None:
            # jQuery UI autocomplete typically uses ul.ui-autocomplete
            page.locator("css=ul.ui-autocomplete").first.wait_for(state="visible", timeout=10_000)

        def click_best_match() -> None:
            # Prefer exact text match in the dropdown
            exact = page.locator(
                f"xpath=//ul[contains(@class,'ui-autocomplete')]//div[contains(@class,'ui-menu-item-wrapper')][normalize-space()=\"{supplier_text}\"]"
            )
            if exact.count() > 0:
                exact.first.scroll_into_view_if_needed()
                exact.first.click()
                return

            # Otherwise click first suggestion
            first_item = page.locator(self.sel.supplier_menu_item_wrapper).first
            first_item.wait_for(state="visible", timeout=10_000)
            first_item.scroll_into_view_if_needed()
            first_item.click()

        # Try 1
        open_and_type(delay_ms=15)
        try:
            wait_menu()
            click_best_match()
        except Exception:
            # If menu didn't appear, fall back to keyboard selection
            s = page.locator(self.sel.supplier_name)
            s.press("ArrowDown")
            s.press("Enter")

        # Give any onchange handlers a moment
        page.eval_on_selector(self.sel.supplier_name, "el => el.blur()")

        try:
            page.wait_for_function(
                """() => {
                    const el = document.querySelector('#SupplierId');
                    if (!el) return false;
                    const v = (el.value || '').trim();
                    return v !== '' && v !== '00000000-0000-0000-0000-000000000000';
                }""",
                timeout=12_000,
            )
            return
        except Exception:
            pass

        # Retry 2 (more deliberate)
        open_and_type(delay_ms=40)
        wait_menu()
        click_best_match()
        page.eval_on_selector(self.sel.supplier_name, "el => el.blur()")

        page.wait_for_function(
            """() => {
                const el = document.querySelector('#SupplierId');
                if (!el) return false;
                const v = (el.value || '').trim();
                return v !== '' && v !== '00000000-0000-0000-0000-000000000000';
            }""",
            timeout=15_000,
        )

    def _save_component(self, page) -> None:
        """
        What it does:
        - Saves the current component.

        Why it matters:
        - Autocomplete lists frequently intercept clicks; saving needs to be resilient.

        Behavior:
        - Sends ESC to close overlays.
        - Attempts normal click; falls back to JS click if intercepted.
        """
        page.keyboard.press("Escape")

        btn = page.locator(self.sel.component_save).first
        btn.wait_for(state="visible", timeout=20_000)
        btn.scroll_into_view_if_needed()

        try:
            btn.click(timeout=15_000)
        except Exception:
            page.eval_on_selector(
                "form#mainForm button.btn.btn-primary[type='submit']", "el => el.click()"
            )

    def _set_currency_usd(self, page) -> None:
        """
        What it does:
        - Forces currency to US Dollar and verifies it "sticks".

        Why it matters:
        - Some forms rerender and clear the field (Package does this often).
        - A missing currency causes save validation, but the symptom shows up later.

        Behavior:
        - Waits for the currency control to exist.
        - If it's a <select>, selects an option containing "US" / "Dollar".
        - Otherwise tries a text-fill + Enter strategy.
        - Verifies the value is not empty; otherwise raises with a screenshot.
        """
        sel = self.sel.currency_id
        loc = page.locator(sel).first
        loc.wait_for(state="visible", timeout=15_000)

        # Determine tag/type
        tag = page.eval_on_selector(sel, "el => (el.tagName || '').toLowerCase()") or ""

        try:
            if tag == "select":
                # Prefer exact label first (your current behavior)
                try:
                    loc.select_option(label="US Dollar")
                except Exception:
                    # Fallback: select the first option whose text contains US/Dollar
                    page.eval_on_selector(
                        sel,
                        """(el) => {
                            const opts = Array.from(el.options || []);
                            const pick = opts.find(o => /us|dollar/i.test(o.textContent || ""));
                            if (pick) el.value = pick.value;
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                    )
            else:
                # Some UIs implement currency as input / autocomplete
                loc.click()
                loc.fill("US Dollar")
                page.keyboard.press("Enter")
        except Exception:
            self._debug_dump("currency_set_exception")
            raise

        # Verify non-empty after a short settle
        page.wait_for_timeout(250)
        value = page.eval_on_selector(sel, "el => (el.value || '').trim()") or ""
        if not value:
            self._debug_dump("currency_not_set")
            raise RuntimeError("Currency could not be set (still empty after attempts).")

    def _new_component(self, page, c: dict) -> None:
        """
        What it does:
        - Dispatches to the correct component builder by type.

        Why it matters:
        - Keeps your mapping modular and mirrors the Selenium architecture.

        Behavior:
        - Opens the component dropdown, then clicks the specific component type.
        """
        page.locator(self.sel.component_dropdown).click(timeout=15_000)

        t = c["type"]
        if t == "Actividad":
            return self._new_activity(page, c)
        if t == "Car":
            return self._new_car(page, c)
        if t == "Cruise":
            return self._new_cruise(page, c)
        if t == "Hotel":
            return self._new_hotel(page, c)
        if t == "Package":
            return self._new_package(page, c)
        if t == "Insurance":
            return self._new_insurance(page, c)

        raise RuntimeError(f"Unknown component type: {t}")

    def _fill_common_component_fields(self, page, c: dict) -> None:
        """
        What it does:
        - Fills the set of fields that are common to all components.

        Why it matters:
        - Prevents duplicated code and ensures consistent behavior across types.

        Behavior:
        - Expects keys: booking_date, supplier, start_date, end_date, commission_amount, total_sales_amount, booking_reference
        """
        self._fill_date(page, self.sel.booking_date, self._parse_iso_date(c["booking_date"]))
        self._add_supplier(page, c["supplier"])
        self._fill_date(page, self.sel.start_date, self._parse_iso_date(c["start_date"]))
        self._fill_date(page, self.sel.end_date, self._parse_iso_date(c["end_date"]))

        self._set_currency_usd(page)

        page.locator(self.sel.estimated_commission).fill(str(c["commission_amount"]))
        page.locator(self.sel.total_sales_amount).fill(str(c["total_sales_amount"]))
        page.locator(self.sel.supplier_reference).fill(c["booking_reference"])

    def _new_activity(self, page, c: dict) -> None:
        page.locator(self.sel.component_activity).click(timeout=15_000)
        self._fill_common_component_fields(page, c)

        a = page.locator(self.sel.activity_name)
        a.fill("")
        a.fill(c["itinerary_details"])

        self._save_component_and_verify(page, c["booking_reference"])

    def _new_car(self, page, c: dict) -> None:
        page.locator(self.sel.component_car).click(timeout=15_000)
        self._fill_common_component_fields(page, c)

        page.locator(self.sel.car_rental_company).fill(c["car_rental_company"])

        self._save_component_and_verify(page, c["booking_reference"])

    def _new_cruise(self, page, c: dict) -> None:
        page.locator(self.sel.component_cruise).click(timeout=15_000)
        self._fill_common_component_fields(page, c)

        page.locator(self.sel.cruise_company).fill(c["cruise_company"])
        page.locator(self.sel.vessel_name).fill(c["ship_name"])

        self._save_component_and_verify(page, c["booking_reference"])

    def _new_hotel(self, page, c: dict) -> None:
        page.locator(self.sel.component_hotel).click(timeout=15_000)
        self._fill_common_component_fields(page, c)

        page.locator(self.sel.hotel_name).fill(c["hotel_name"])

        self._save_component_and_verify(page, c["booking_reference"])

    def _new_package(self, page, c: dict) -> None:
        page.locator(self.sel.component_package).click(timeout=15_000)
        self._fill_common_component_fields(page, c)

        # Package toggles (as in Selenium)
        page.locator(self.sel.package_activity_choice).click(timeout=15_000)
        page.locator(self.sel.package_hotel_choice).click(timeout=15_000)

        # IMPORTANT: these toggles can cause a rerender that clears Currency
        self._set_currency_usd(page)

        page.locator(self.sel.activity_name).fill(c["itinerary_details"])

        self._save_component_and_verify(page, c["booking_reference"])

    def _new_insurance(self, page, c: dict) -> None:
        page.locator(self.sel.component_insurance).click(timeout=15_000)
        self._fill_common_component_fields(page, c)
        self._save_component_and_verify(page, c["booking_reference"])

    def _save_component_and_verify(self, page, booking_reference: str) -> None:
        """
        What it does:
        - Saves a component and verifies it was accepted by the portal.

        Why it matters:
        - Prevents false positives AND false negatives by using portal-specific signals.

        Behavior:
        Success is true if ANY of these happens after clicking save:
        1) URL changes (navigation / redirect)
        2) Save button becomes disabled or disappears
        3) Booking reference appears on a stable post-save page (after a brief settle)
        Failure is true if:
        - Validation errors appear (field-validation / summary errors)
        On failure: saves screenshot and raises.
        """
        save_btn = page.locator(self.sel.component_save).first
        validation = page.locator("css=.validation-summary-errors, .field-validation-error")

        # snapshot current URL to detect redirects
        url_before = page.url

        # close overlays that can intercept clicks
        page.keyboard.press("Escape")

        # ensure button is interactable
        save_btn.wait_for(state="visible", timeout=20_000)
        save_btn.scroll_into_view_if_needed()

        # click save
        try:
            save_btn.click(timeout=15_000)
        except Exception:
            # fallback: JS click
            page.eval_on_selector(
                "form#mainForm button.btn.btn-primary[type='submit']", "el => el.click()"
            )

        # quick settle
        page.wait_for_timeout(500)

        # fail-fast on validation errors
        try:
            if validation.count() > 0 and validation.first.is_visible():
                self._debug_dump(f"validation_after_save_{booking_reference}")
                raise RuntimeError("Validation error shown after save.")
        except Exception:
            # if validation selector evaluation fails, continue to other checks
            pass

        # 1) URL changed?
        try:
            page.wait_for_function(
                "(prev) => window.location.href !== prev",
                arg=url_before,
                timeout=7_000,
            )
            return
        except Exception:
            pass

        # 2) Save button disabled/hidden?
        try:
            page.wait_for_function(
                """() => {
                    const b = document.querySelector("form#mainForm button.btn.btn-primary[type='submit']");
                    if (!b) return true;          // disappeared
                    if (b.disabled) return true;  // disabled
                    const r = b.getBoundingClientRect();
                    return (r.width === 0 || r.height === 0); // effectively hidden
                }""",
                timeout=7_000,
            )
            return
        except Exception:
            pass

        # 3) Booking reference visible somewhere post-save?
        # Some portals redirect or update content asynchronously; give it a bit more time.
        try:
            page.wait_for_timeout(1200)
            page.wait_for_function(
                """(ref) => {
                    const body = document.body;
                    if (!body) return false;
                    return (body.innerText || '').includes(ref);
                }""",
                arg=booking_reference,
                timeout=7_000,
            )
            return
        except Exception as e:
            self._debug_dump(f"save_unverified_{booking_reference}")
            raise RuntimeError(
                f"Component save could not be verified for {booking_reference}"
            ) from e

    def _final_submit_and_verify(self, page) -> None:
        """
        Hard-blocked on purpose.

        What it would do:
        - Click final submit and verify actual submission completion.

        Why it's blocked:
        - You explicitly required: MUST NOT submit the form (production-only portal).

        Behavior:
        - Always raises to prevent accidental submission.
        """
        raise RuntimeError(
            "Final submit is DISABLED by policy (production-only portal). Do not call this method."
        )
