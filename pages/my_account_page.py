from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, expect

from pages.auth_page import AuthPage
from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class ProfileDetails:
    first_name: str
    last_name: str
    telephone: str
    day: str
    month: str
    year: str


@dataclass(frozen=True)
class OrderDetailsSnapshot:
    order_number: str
    status_text: str
    date_placed_text: str
    shipping_text: str
    payment_text: str
    email_text: str


@dataclass(frozen=True)
class AddressData:
    first_name: str
    last_name: str
    line1: str
    line2: str
    postcode: str
    town: str
    region: str = ""
    company: str = ""


@dataclass(frozen=True)
class LoqateAttemptResult:
    suggestions_visible: bool
    populated: bool
    line1: str
    postcode: str
    town: str


class MyAccountPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.auth = AuthPage(page)

    def open_account_home(self, account_home_url: str, email: str, password: str, timeout: int = 60000):
        self.page.goto(account_home_url, wait_until="domcontentloaded", timeout=timeout)
        self._dismiss_cookie_blockers()

        login_form = self.page.locator(AuthPage.LOGIN_FORM_SELECTOR).first
        if login_form.count() > 0 and login_form.is_visible():
            self._dismiss_cookie_blockers()
            self.auth.login(email=email, password=password, timeout=timeout)
            self._dismiss_cookie_blockers()

        expect(self.page).to_have_url(re.compile(r".*/my-account/(?:home|orders|address-book|update-)"), timeout=timeout)
        self._wait_my_account_shell(timeout=timeout)

    def open_order_history(self, timeout: int = 45000):
        self._open_my_account_section(
            link_name_pattern=r"order\s*history",
            fallback_path="/en_GB/my-account/orders",
            expected_url_pattern=r".*/my-account/orders(?:$|[/?#])",
            timeout=timeout,
        )

    def sort_order_history(self, value: str, timeout: int = 45000) -> str:
        select = self.page.locator("select[name='sort']").first
        expect(select).to_be_visible(timeout=timeout)
        select.select_option(value=value)
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(500)
        return select.input_value()

    def open_first_order(self, timeout: int = 45000) -> str:
        order_links = self.page.locator("a.order-history__order-id")
        count = order_links.count()
        assert count > 0, "Order History is empty. Expected at least one order."

        first = order_links.first
        expect(first).to_be_visible(timeout=timeout)
        order_code = first.inner_text().strip()
        self._click_and_wait(first, timeout=timeout)
        expect(self.page).to_have_url(re.compile(r".*/my-account/order/"), timeout=timeout)
        return order_code

    def read_order_details(self, timeout: int = 20000) -> OrderDetailsSnapshot:
        heading = self.page.get_by_role("heading", name=re.compile(r"order\s*number", re.I)).first
        expect(heading).to_be_visible(timeout=timeout)
        heading_text = heading.inner_text().strip()
        match = re.search(r"(GB\d+)", heading_text)
        order_number = match.group(1) if match else heading_text
        return OrderDetailsSnapshot(
            order_number=order_number,
            status_text=self._text_or_empty(r"order\s*status"),
            date_placed_text=self._text_or_empty(r"date\s*placed"),
            shipping_text=self._text_or_empty(r"shipping\s*method"),
            payment_text=self._text_or_empty(r"payment\s*method"),
            email_text=self._text_or_empty(r"email"),
        )

    def click_reorder_if_available(self, timeout: int = 45000) -> tuple[bool, str]:
        reorder = self.page.get_by_role("link", name=re.compile(r"^\s*reorder\s*$", re.I)).first
        if reorder.count() == 0 or not reorder.is_visible():
            reorder = self.page.get_by_role("button", name=re.compile(r"^\s*reorder\s*$", re.I)).first
        if reorder.count() == 0 or not reorder.is_visible():
            return False, self.page.url

        self._click_and_wait(reorder, timeout=timeout)
        return True, self.page.url

    def click_back_to_your_account(self, timeout: int = 45000) -> str:
        back = self.page.get_by_role("link", name=re.compile(r"back\s*to\s*your\s*account", re.I)).first
        if back.count() > 0 and back.is_visible():
            self._click_and_wait(back, timeout=timeout)
        else:
            self.page.goto(self._url("/en_GB/my-account/home"), wait_until="domcontentloaded", timeout=timeout)
        expect(self.page).to_have_url(re.compile(r".*/my-account/home(?:$|[/?#])"), timeout=timeout)
        return self.page.url

    def open_update_personal_details(self, timeout: int = 45000):
        self._open_my_account_section(
            link_name_pattern=r"personal\s*details",
            fallback_path="/en_GB/my-account/update-profile",
            expected_url_pattern=r".*/my-account/update-profile(?:$|[/?#])",
            timeout=timeout,
        )
        expect(self.page.locator("#profile\\.firstName").first).to_be_visible(timeout=timeout)

    def read_profile_details(self) -> ProfileDetails:
        return ProfileDetails(
            first_name=self._value_or_empty("#profile\\.firstName"),
            last_name=self._value_or_empty("#profile\\.lastName"),
            telephone=self._value_or_empty("#profile\\.telephone"),
            day=self._select_value_or_empty("#day"),
            month=self._select_value_or_empty("#month"),
            year=self._select_value_or_empty("#year"),
        )

    def fill_profile_details(self, profile: ProfileDetails):
        self.page.locator("#profile\\.firstName").first.fill(profile.first_name)
        self.page.locator("#profile\\.lastName").first.fill(profile.last_name)
        self.page.locator("#profile\\.telephone").first.fill(profile.telephone)
        self._select_if_present("#day", profile.day)
        self._select_if_present("#month", profile.month)
        self._select_if_present("#year", profile.year)

    def clear_profile_required_fields(self):
        self.page.locator("#profile\\.firstName").first.fill("")
        self.page.locator("#profile\\.lastName").first.fill("")

    def submit_profile_update(self, timeout: int = 45000):
        update = self.page.get_by_role("button", name=re.compile(r"^\s*update\s*$", re.I)).first
        expect(update).to_be_visible(timeout=timeout)
        self._click_and_wait(update, timeout=timeout)

    def open_update_email(self, timeout: int = 45000):
        self._open_my_account_section(
            link_name_pattern=r"update\s*email",
            fallback_path="/en_GB/my-account/update-email",
            expected_url_pattern=r".*/my-account/update-email(?:$|[/?#])",
            timeout=timeout,
        )
        expect(self.page.locator("#profile\\.email").first).to_be_visible(timeout=timeout)

    def submit_update_email(self, new_email: str, password: str, timeout: int = 45000):
        self.page.locator("#profile\\.email").first.fill(new_email)
        self.page.locator("#profile\\.checkEmail").first.fill(new_email)
        self.page.locator("#profile\\.pwd").first.fill(password)
        update = self.page.get_by_role("button", name=re.compile(r"^\s*update\s*$", re.I)).first
        expect(update).to_be_visible(timeout=timeout)
        self._click_and_wait(update, timeout=timeout)

    def submit_update_email_empty(self, timeout: int = 45000):
        self.page.locator("#profile\\.email").first.fill("")
        self.page.locator("#profile\\.checkEmail").first.fill("")
        self.page.locator("#profile\\.pwd").first.fill("")
        update = self.page.get_by_role("button", name=re.compile(r"^\s*update\s*$", re.I)).first
        expect(update).to_be_visible(timeout=timeout)
        update.click()
        self.page.wait_for_timeout(800)

    def open_update_password(self, timeout: int = 45000):
        self._open_my_account_section(
            link_name_pattern=r"update\s*password",
            fallback_path="/en_GB/my-account/update-password",
            expected_url_pattern=r".*/my-account/update-password(?:$|[/?#])",
            timeout=timeout,
        )
        expect(self.page.locator("#currentPassword").first).to_be_visible(timeout=timeout)

    def submit_update_password(self, current_password: str, new_password: str, timeout: int = 45000):
        self.page.locator("#currentPassword").first.fill(current_password)
        self.page.locator("#newPassword").first.fill(new_password)
        self.page.locator("#checkNewPassword").first.fill(new_password)
        update = self.page.get_by_role("button", name=re.compile(r"^\s*update\s*$", re.I)).first
        expect(update).to_be_visible(timeout=timeout)
        self._click_and_wait(update, timeout=timeout)

    def submit_update_password_empty(self, timeout: int = 45000):
        self.page.locator("#currentPassword").first.fill("")
        self.page.locator("#newPassword").first.fill("")
        self.page.locator("#checkNewPassword").first.fill("")
        update = self.page.get_by_role("button", name=re.compile(r"^\s*update\s*$", re.I)).first
        expect(update).to_be_visible(timeout=timeout)
        update.click()
        self.page.wait_for_timeout(800)

    def open_address_book(self, timeout: int = 45000):
        self._open_my_account_section(
            link_name_pattern=r"address\s*book",
            fallback_path="/en_GB/my-account/address-book",
            expected_url_pattern=r".*/my-account/address-book(?:$|[/?#])",
            timeout=timeout,
        )
        expect(self.page.get_by_role("heading", name=re.compile(r"address\s*book", re.I)).first).to_be_visible(
            timeout=timeout
        )

    def open_add_address(self, timeout: int = 45000):
        add = self.page.get_by_role("link", name=re.compile(r"add\s*address", re.I)).first
        if add.count() == 0 or not add.is_visible():
            self.page.goto(self._url("/en_GB/my-account/add-address"), wait_until="domcontentloaded", timeout=timeout)
        else:
            self._click_and_wait(add, timeout=timeout)
        expect(self.page).to_have_url(re.compile(r".*/my-account/(?:add-address|edit-address/.*)"), timeout=timeout)
        expect(self.page.locator("#epsonAddressForm").first).to_be_visible(timeout=timeout)

    def switch_to_manual_address_mode(self, timeout: int = 10000):
        manual_toggle = self.page.locator(
            "a.js-address-finder-toggler[data-address-finder-toggle='off'], "
            "button.js-address-finder-toggler[data-address-finder-toggle='off']"
        ).first
        if manual_toggle.count() == 0 or not manual_toggle.is_visible():
            manual_toggle = self.page.get_by_role("link", name=re.compile(r"enter\s*address\s*manually", re.I)).first
        if manual_toggle.count() == 0 or not manual_toggle.is_visible():
            manual_toggle = self.page.get_by_role("button", name=re.compile(r"enter\s*address\s*manually", re.I)).first

        if manual_toggle.count() > 0 and manual_toggle.is_visible():
            try:
                manual_toggle.click()
            except PlaywrightError:
                handle = manual_toggle.element_handle()
                if handle:
                    self.page.evaluate("(el) => el.click()", handle)

        fields_container = self.page.locator(".js-address-finder-fields-container:not(.hidden)").first
        if fields_container.count() > 0:
            expect(fields_container).to_be_visible(timeout=timeout)
        expect(self.page.locator("#line-1").first).to_be_visible(timeout=timeout)
        expect(self.page.locator("#postcode").first).to_be_visible(timeout=timeout)

    def fill_address_form(self, address: AddressData):
        self.page.locator("#first-name").first.fill(address.first_name)
        self.page.locator("#last-name").first.fill(address.last_name)
        if self.page.locator("#company-name").first.count() > 0:
            self.page.locator("#company-name").first.fill(address.company)
        self.page.locator("#line-1").first.fill(address.line1)
        self.page.locator("#line-2").first.fill(address.line2)
        self.page.locator("#postcode").first.fill(address.postcode)
        self.page.locator("#town").first.fill(address.town)
        if address.region and self.page.locator("#region").first.count() > 0:
            self.page.locator("#region").first.fill(address.region)

    def clear_address_required_fields(self):
        self.page.locator("#line-1").first.fill("")
        self.page.locator("#postcode").first.fill("")
        self.page.locator("#town").first.fill("")

    def save_address(self, timeout: int = 45000):
        save_button = self.page.get_by_role("button", name=re.compile(r"^\s*save\s*$", re.I)).first
        expect(save_button).to_be_visible(timeout=timeout)
        self._click_and_wait(save_button, timeout=timeout)

    def cancel_address(self, timeout: int = 45000):
        cancel_link = self.page.get_by_role("link", name=re.compile(r"^\s*cancel\s*$", re.I)).first
        expect(cancel_link).to_be_visible(timeout=timeout)
        self._click_and_wait(cancel_link, timeout=timeout)
        expect(self.page).to_have_url(re.compile(r".*/my-account/address-book(?:$|[/?#])"), timeout=timeout)

    def address_exists(self, line1: str) -> bool:
        return self._address_card_by_line1(line1) is not None

    def open_edit_address(self, line1: str, timeout: int = 45000):
        card = self._require_address_card(line1=line1)
        edit = card.get_by_role("link", name=re.compile(r"edit", re.I)).first
        if edit.count() == 0:
            edit = card.locator("a[href*='edit-address']").first
        expect(edit).to_be_visible(timeout=timeout)
        self._click_and_wait(edit, timeout=timeout)
        expect(self.page).to_have_url(re.compile(r".*/my-account/edit-address/"), timeout=timeout)
        expect(self.page.locator("#epsonAddressForm").first).to_be_visible(timeout=timeout)

    def delete_address(self, line1: str, timeout: int = 45000):
        card = self._require_address_card(line1=line1)
        delete = card.get_by_role("button", name=re.compile(r"delete\s*address|delete", re.I)).first
        if delete.count() == 0:
            delete = card.locator(
                "[aria-label*='Delete' i], a[aria-label*='Delete' i], button.delete-address, a[data-modal-target]"
            ).first
        expect(delete).to_be_visible(timeout=timeout)
        modal_target = delete.get_attribute("data-modal-target") or ""
        try:
            delete.click()
        except PlaywrightError:
            handle = delete.element_handle()
            if handle:
                self.page.evaluate("(el) => el.click()", handle)

        confirm = None
        if modal_target:
            modal = self.page.locator(f"[data-modal='{modal_target}']").first
            if modal.count() > 0:
                try:
                    expect(modal).to_be_visible(timeout=5000)
                except AssertionError:
                    pass
                candidate = modal.locator("a[href*='remove-address']").first
                if candidate.count() > 0:
                    confirm = candidate

        if confirm is None:
            visible_confirm = self.page.locator("a[href*='remove-address']:visible").first
            if visible_confirm.count() > 0:
                confirm = visible_confirm

        if confirm is None:
            fallback = self.page.locator("a[href*='remove-address']").first
            if fallback.count() > 0:
                confirm = fallback

        if confirm is None:
            raise AssertionError("Delete confirmation action was not found for selected address")

        try:
            self._click_and_wait(confirm, timeout=timeout)
        except PlaywrightError:
            handle = confirm.element_handle()
            if not handle:
                raise
            before = self.page.url
            self.page.evaluate("(el) => el.click()", handle)
            if self.page.url == before:
                self.page.wait_for_load_state("domcontentloaded")

    def attempt_loqate_autofill(self, postcode: str, timeout: int = 15000) -> LoqateAttemptResult:
        finder = self.page.locator("#address-finder").first
        expect(finder).to_be_visible(timeout=timeout)
        finder.click()
        finder.fill(postcode)
        self.page.wait_for_timeout(1200)

        suggestions = self.page.locator(".pcaitem, [class*='pcaitem'], .pca .pcatext, .pca ul li")
        suggestions_visible = suggestions.count() > 0 and suggestions.first.is_visible()

        if suggestions_visible:
            try:
                suggestions.first.click(timeout=3000)
            except PlaywrightError:
                finder.press("ArrowDown")
                finder.press("Enter")
        else:
            finder.press("ArrowDown")
            finder.press("Enter")

        self.page.wait_for_timeout(1800)
        line1 = self._value_or_empty("#line-1")
        town = self._value_or_empty("#town")
        postcode_value = self._value_or_empty("#postcode")
        populated = bool(line1 and town and postcode_value)
        return LoqateAttemptResult(
            suggestions_visible=suggestions_visible,
            populated=populated,
            line1=line1,
            postcode=postcode_value,
            town=town,
        )

    def collect_visible_form_errors(self) -> list[str]:
        errors = self.page.eval_on_selector_all(
            ".form__error, .help-block, .invalid-feedback, .form-errors li, .alert-danger, .global-alerts .alert",
            """
            (nodes) => {
              const out = [];
              for (const node of nodes) {
                const style = window.getComputedStyle(node);
                if (style && (style.display === 'none' || style.visibility === 'hidden')) continue;
                const text = (node.textContent || '').trim();
                if (text) out.push(text);
              }
              return out;
            }
            """,
        )
        deduped: list[str] = []
        seen: set[str] = set()
        for item in errors:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def success_alert_visible(self) -> bool:
        alert = self.page.locator(
            ".alert-success, .global-alerts .alert-success, .alert.alert-success, .notification-positive"
        ).first
        return alert.count() > 0 and alert.is_visible()

    def logout(self, timeout: int = 45000):
        self.page.goto(self._url("/en_GB/logout"), wait_until="domcontentloaded", timeout=timeout)
        dismiss_onetrust(self.page)

    def _open_my_account_section(
        self,
        link_name_pattern: str,
        fallback_path: str,
        expected_url_pattern: str,
        timeout: int = 45000,
    ):
        self._dismiss_cookie_blockers()
        link = self.page.get_by_role("link", name=re.compile(link_name_pattern, re.I)).first
        if link.count() > 0 and link.is_visible():
            self._click_and_wait(link, timeout=timeout)
        else:
            self.page.goto(self._url(fallback_path), wait_until="domcontentloaded", timeout=timeout)
        self._dismiss_cookie_blockers()
        expect(self.page).to_have_url(re.compile(expected_url_pattern), timeout=timeout)

    def _click_and_wait(self, target: Locator, timeout: int = 45000):
        self._dismiss_cookie_blockers()
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
                target.click()
        except PlaywrightError:
            target.click()
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_timeout(500)
        self._dismiss_cookie_blockers()

    def _wait_my_account_shell(self, timeout: int = 30000):
        expect(self.page).to_have_url(re.compile(r".*/my-account/"), timeout=timeout)
        login_form = self.page.locator(AuthPage.LOGIN_FORM_SELECTOR).first
        if login_form.count() > 0:
            expect(login_form).to_be_hidden(timeout=timeout)

    def _address_card_by_line1(self, line1: str) -> Locator | None:
        cards = self.page.locator(".address-list__address")
        for idx in range(cards.count()):
            card = cards.nth(idx)
            text = card.inner_text().strip().lower()
            if line1.strip().lower() in text:
                return card
        return None

    def _require_address_card(self, line1: str) -> Locator:
        card = self._address_card_by_line1(line1=line1)
        if card is None:
            raise AssertionError(f"Address with line1='{line1}' was not found in Address Book")
        return card

    def _text_or_empty(self, field_name_pattern: str) -> str:
        node = self.page.get_by_text(re.compile(rf"{field_name_pattern}\s*:", re.I)).first
        if node.count() == 0:
            return ""
        return node.inner_text().strip()

    def _value_or_empty(self, selector: str) -> str:
        field = self.page.locator(selector).first
        if field.count() == 0:
            return ""
        return field.input_value().strip()

    def _select_value_or_empty(self, selector: str) -> str:
        dropdown = self.page.locator(selector).first
        if dropdown.count() == 0:
            return ""
        return dropdown.input_value().strip()

    def _select_if_present(self, selector: str, value: str):
        if not value:
            return
        dropdown = self.page.locator(selector).first
        if dropdown.count() == 0:
            return
        try:
            dropdown.select_option(value=value)
        except PlaywrightError:
            pass

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _dismiss_cookie_blockers(self):
        dismiss_onetrust(self.page)
        try:
            accept = self.page.locator("#onetrust-accept-btn-handler").first
            if accept.count() > 0 and accept.is_visible():
                accept.click(timeout=1500)
        except PlaywrightError:
            pass
        try:
            self.page.evaluate(
                """
                () => {
                  const sdk = document.querySelector('#onetrust-consent-sdk');
                  if (!sdk) return;
                  const overlay = sdk.querySelector('.onetrust-pc-dark-filter');
                  if (overlay) overlay.remove();
                }
                """
            )
        except Exception:
            pass
