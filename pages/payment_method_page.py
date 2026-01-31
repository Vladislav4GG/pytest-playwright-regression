import re
from playwright.sync_api import Page, expect


class PaymentMethodPage:
    def __init__(self, page: Page):
        self.page = page

    def select_credit_card(self):
        radio = self.page.locator('input[name="paymentMethod"][value="adyen_cc"]')
        details = self.page.locator("#dd_method_adyen_cc")

        expect(radio).to_be_attached(timeout=20000)

        rid = radio.get_attribute("id")
        label = self.page.locator(f"label[for='{rid}']") if rid else None

        if label and label.count() > 0:
            label.scroll_into_view_if_needed()
            label.click()
        else:
            radio.scroll_into_view_if_needed()
            radio.click()

        if not radio.is_checked():
            radio.dispatch_event("change")

        expect(radio).to_be_checked(timeout=10000)

        def wait_details_open(timeout=20000):
            self.page.wait_for_function(
                """() => {
                    const el = document.querySelector('#dd_method_adyen_cc');
                    if (!el) return false;
                    const st = getComputedStyle(el);
                    return st.display !== 'none' && st.visibility !== 'hidden';
                }""",
                timeout=timeout
            )

        try:
            wait_details_open(timeout=15000)
        except Exception:
            wrapper_title = radio.locator(
                "xpath=ancestor::div[contains(@class,'payment-method__wrapper')]"
            ).locator(".payment-method__title")
            if wrapper_title.count() > 0:
                wrapper_title.click()
            try:
                wait_details_open(timeout=10000)
            except Exception:
                self.page.evaluate("""
                () => {
                  const el = document.querySelector('#dd_method_adyen_cc');
                  if (el) el.style.display = 'block';
                }
                """)
                wait_details_open(timeout=5000)

        card_div = self.page.locator("#dd_method_adyen_cc #card-div").first
        expect(card_div).to_be_attached(timeout=20000)

        iframe_number = self.page.locator("iframe[title='Iframe for secured card number']")
        iframe_exp = self.page.locator("iframe[title='Iframe for secured card expiry date']")
        iframe_cvc = self.page.locator("iframe[title='Iframe for secured card security code']")

        expect(iframe_number).to_be_attached(timeout=30000)
        expect(iframe_exp).to_be_attached(timeout=30000)
        expect(iframe_cvc).to_be_attached(timeout=30000)

    def fill_card(self, number: str, expiry: str, cvc: str, holder: str):
        card_frame = self.page.frame_locator("iframe[title='Iframe for secured card number']")
        card_input = card_frame.locator("input[data-fieldtype='encryptedCardNumber']")
        expect(card_input).to_be_visible(timeout=30000)
        expect(card_input).to_be_editable(timeout=30000)
        card_input.fill(number)

        exp_frame = self.page.frame_locator("iframe[title='Iframe for secured card expiry date']")
        exp_input = exp_frame.locator("input[data-fieldtype='encryptedExpiryDate']")
        expect(exp_input).to_be_visible(timeout=30000)
        expect(exp_input).to_be_editable(timeout=30000)
        exp_input.fill(expiry)

        cvc_frame = self.page.frame_locator("iframe[title='Iframe for secured card security code']")
        cvc_input = cvc_frame.locator("input[data-fieldtype='encryptedSecurityCode']")
        expect(cvc_input).to_be_visible(timeout=30000)
        expect(cvc_input).to_be_editable(timeout=30000)
        cvc_input.fill(cvc)

        holder_input = self.page.locator("#dd_method_adyen_cc input[name='holderName']")
        expect(holder_input).to_be_editable(timeout=20000)
        holder_input.fill(holder)

    def click_next(self):
        candidates = [
            # submit у формі Adyen
            self.page.locator("form#adyen-encrypted-form button[type='submit']"),
            self.page.locator("form#adyen-encrypted-form input[type='submit']"),

            # частий випадок на SFCC/checkout
            self.page.locator("button.js-continue-checkout-button"),
            self.page.locator("[data-checkout-url]"),

            # role-based fallback
            self.page.get_by_role("button", name=re.compile(r"^(Next|Continue|Review order|Proceed|Place order)$", re.I)),
            self.page.get_by_role("button", name=re.compile(r"continue to summary|summary|next", re.I)),
        ]

        for loc in candidates:
            if loc.count() == 0:
                continue
            btn = loc.first
            if not btn.is_visible():
                continue

            btn.scroll_into_view_if_needed()

            # якщо це елемент з data-checkout-url — просто переходимо по ньому
            if btn.get_attribute("data-checkout-url"):
                self.page.goto(btn.get_attribute("data-checkout-url"))
                return

            btn.click()
            return

        raise AssertionError("Next/Continue button not found on payment method page. Need updated selector.")