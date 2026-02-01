import re
from typing import Literal, Optional
from playwright.sync_api import Page, expect, Locator

CardMode = Literal["saved", "new"]

class PaymentMethodPage:
    TITLE_BY_FIELD = {
        "encryptedCardNumber": "Iframe for secured card number",
        "encryptedExpiryDate": "Iframe for secured card expiry date",
        "encryptedSecurityCode": "Iframe for secured card security code",
    }

    def __init__(self, page: Page):
        self.page = page
        self._mode: Optional[CardMode] = None

    # ---------- helpers ----------
    def _click_payment_label(self, text_regex: str, timeout: int = 60000):
        lbl = self.page.locator("label.payment-method__label", has_text=re.compile(text_regex, re.I)).first
        expect(lbl).to_be_visible(timeout=timeout)
        lbl.scroll_into_view_if_needed()
        lbl.click(force=True)

    def _wait_details_open(self, details: Locator, timeout: int = 60000):
        expect(details).to_be_attached(timeout=timeout)
        self.page.wait_for_function(
            """(el) => {
                if (!el) return false;
                const st = getComputedStyle(el);
                return st.display !== 'none' && st.visibility !== 'hidden';
            }""",
            arg=details.element_handle(),
            timeout=timeout,
        )

    def _details_for_payment_method(self) -> Locator:
        # після кліку "Credit Card" може відкритись dd_method_adyen_card або інший dd_method_...
        # найнадійніше — знайти details який містить або саб-опції, або card-div
        return self.page.locator(
            ".payment-method__details.js-chckt-pm__details"
        ).filter(
            has=self.page.locator("input[name='subpaymentMethod'], #card-div")
        ).first

    def _secured_input_in(self, scope_css: str, fieldtype: str) -> Locator:
        iframe_title = self.TITLE_BY_FIELD[fieldtype]
        return (
            self.page
            .frame_locator(f"{scope_css} iframe[title='{iframe_title}']")
            .locator(f"input[data-fieldtype='{fieldtype}']")
        )

    def _type_secured_in(self, scope_css: str, fieldtype: str, value: str, timeout: int = 60000):
        inp = self._secured_input_in(scope_css, fieldtype)
        expect(inp).to_be_visible(timeout=timeout)
        inp.click(force=True)
        inp.fill("")           # інколи Adyen не любить fill без очистки
        inp.type(value, delay=30)

    # ---------- public ----------
    def select_credit_card(self, *, prefer_saved: bool = True, timeout: int = 60000) -> CardMode:
        """
        Працює і для registered (saved + new), і для guest (тільки new).
        Не покладається на value='adyen_card'.
        """
        # 1) клік по "Credit Card"
        self._click_payment_label(r"^\s*Credit Card\s*$", timeout=timeout)

        # 2) чекаємо що реально відкрився потрібний details
        details = self._details_for_payment_method()
        self._wait_details_open(details, timeout=timeout)

        # 3) registered може мати subpaymentMethod, guest часто ні
        saved_inputs = self.page.locator("input[name='subpaymentMethod'][value^='adyen_oneclick_']")
        new_input = self.page.locator("input[name='subpaymentMethod'][value='adyen_cc']").first

        has_saved = saved_inputs.count() > 0
        has_new = new_input.count() > 0

        # --- SAVED ---
        if prefer_saved and has_saved:
            # обираємо *1111 якщо є, інакше перший saved
            label_1111 = self.page.locator("label.payment-method__label", has_text=re.compile(r"\*1111\b", re.I)).first
            if label_1111.count() > 0:
                for_id = label_1111.get_attribute("for")
                if not for_id:
                    raise AssertionError("Saved card label has no 'for' attribute")
                self.page.locator(f"#{for_id}").check(force=True)
                saved_value = self.page.locator(f"#{for_id}").get_attribute("value")
            else:
                saved_value = saved_inputs.first.get_attribute("value")
                saved_inputs.first.check(force=True)

            if not saved_value:
                raise AssertionError("Cannot resolve saved subpaymentMethod value")

            saved_details = self.page.locator(f"#dd_method_{saved_value}").first
            self._wait_details_open(saved_details, timeout=timeout)

            self._mode = "saved"
            return "saved"

        # --- NEW ---
        # якщо є subpaymentMethod=adyen_cc — клікаємо його, якщо нема (guest) — просто чекаємо card-div
        if has_new:
            new_input.check(force=True)
            new_details = self.page.locator("#dd_method_adyen_cc").first
            self._wait_details_open(new_details, timeout=timeout)

        card_div = self.page.locator("#card-div").first
        expect(card_div).to_be_visible(timeout=timeout)

        # головне: переконатися що card number iframe/input реально видимий
        expect(self._secured_input_in("#card-div", "encryptedCardNumber")).to_be_visible(timeout=timeout)

        self._mode = "new"
        return "new"

    def fill_card(self, *, mode: CardMode, number: str, expiry: str, cvc: str, holder: str, timeout: int = 60000):
        if mode == "saved":
            # тільки CVC, і строго всередині видимого oneclick details
            saved_details = self.page.locator("[id^='dd_method_adyen_oneclick_']").filter(
                has=self.page.locator("iframe[title='Iframe for secured card security code']")
            ).filter(
                has_not=self.page.locator("[style*='display: none']")
            ).first

            expect(saved_details).to_be_visible(timeout=timeout)
            details_id = saved_details.get_attribute("id")
            if not details_id:
                raise AssertionError("Cannot get id of saved details")

            self._type_secured_in(f"#{details_id}", "encryptedSecurityCode", cvc, timeout=timeout)
            return

        # NEW card — ВСЕ ТІЛЬКИ В #card-div (щоб не ловити 2 iframes)
        expect(self.page.locator("#card-div")).to_be_visible(timeout=timeout)

        self._type_secured_in("#card-div", "encryptedCardNumber", number, timeout=timeout)
        self._type_secured_in("#card-div", "encryptedExpiryDate", expiry, timeout=timeout)
        self._type_secured_in("#card-div", "encryptedSecurityCode", cvc, timeout=timeout)

        holder_input = self.page.locator("input[name='holderName']").first
        expect(holder_input).to_be_visible(timeout=timeout)
        holder_input.fill(holder)

    def click_next(self, timeout: int = 60000):
        btn = self.page.get_by_role("button", name=re.compile(r"^\s*Next\s*$", re.I)).first
        expect(btn).to_be_enabled(timeout=timeout)
        btn.click()