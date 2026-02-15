# pages/return_order_page.py
from typing import Literal
from playwright.sync_api import Page, expect

ReturnLabelMode = Literal["email", "digital"]


class ReturnOrderPage:
    def __init__(self, page: Page):
        self.page = page

    def choose_return_label(self, mode: ReturnLabelMode = "email"):
        """
        Step: Return Label
        - email   -> EMAIL_PRINTED_LABEL
        - digital -> EMAIL_DIGITAL_LABEL
        """
        mapping = {
            "email": "EMAIL_PRINTED_LABEL",
            "digital": "EMAIL_DIGITAL_LABEL",
        }
        value = mapping[mode]

        radio = self.page.locator(
            "input.js-return-label-options[name='returnLabelType'][value='%s']" % value
        ).first

        # ❗ radio hidden — ТІЛЬКИ attached, НЕ visible
        expect(radio).to_be_attached(timeout=30000)

        # якщо вже вибрано — нічого не робимо
        try:
            if radio.is_checked():
                return
        except Exception:
            pass

        # 1️⃣ основний шлях — клікаємо label
        radio_id = radio.get_attribute("id")
        if radio_id:
            label = self.page.locator(f"label[for='{radio_id}']").first
            if label.count() > 0:
                expect(label).to_be_visible(timeout=30000)
                label.scroll_into_view_if_needed()
                label.click()
                expect(radio).to_be_checked(timeout=10000)
                return

        # 2️⃣ fallback — force check
        radio.check(force=True)
        expect(radio).to_be_checked(timeout=10000)

    def confirm_return_three_steps(self, *, label_mode: ReturnLabelMode = "email"):
        """
        У вас 3 екрани підряд з однаковою кнопкою confirm.
        На одному з кроків є вибір return label — там і перемикаємо.
        """
        for step in range(3):
            # якщо на цьому кроці є return label radios — обираємо
            radios = self.page.locator("input.js-return-label-options[name='returnLabelType']")
            if radios.count() > 0:
                self.choose_return_label(label_mode)

            btn = self.page.locator("button.js-return-order-confirm-button").first
            expect(btn).to_be_visible(timeout=30000)
            expect(btn).to_be_enabled(timeout=30000)

            btn.scroll_into_view_if_needed()
            btn.click()

            self.page.wait_for_load_state("domcontentloaded")