from playwright.sync_api import Page, expect
import re


class DeliveryAddressPage:
    def __init__(self, page: Page):
        self.page = page

    def _ensure_manual_address_visible(self):
        # Часто поля сховані, поки не обрати manual entry
        manual_candidates = [
            self.page.get_by_role("button", name="Enter address manually"),
            self.page.get_by_role("link", name="Enter address manually"),
            self.page.get_by_text("Enter address manually"),
            self.page.get_by_text("Manual address"),
            self.page.get_by_text("Enter manually"),
        ]

        for c in manual_candidates:
            try:
                if c.first.is_visible():
                    c.first.click()
                    break
            except Exception:
                pass

        # Якщо є секція/акордеон — просто гарантуємо що line-1 видиме
        line1_visible = self.page.locator("#line-1:visible")
        expect(line1_visible).to_be_visible()

    def fill_and_continue(self, first: str, last: str, line1: str, town: str, postcode: str):
        # дочекайся що це саме address page
        expect(self.page).to_have_url(re.compile(r".*/checkout/multi/delivery-address/.*"))

        self._ensure_manual_address_visible()

        self.page.locator("#first-name:visible").fill(first)
        self.page.locator("#last-name:visible").fill(last)
        self.page.locator("#line-1:visible").fill(line1)
        self.page.locator("#town:visible").fill(town)
        self.page.locator("#postcode:visible").fill(postcode)

        # кнопка може називатись по-різному, але зазвичай Save and Continue
        btn = self.page.get_by_role("button", name="Save and Continue")
        expect(btn).to_be_visible()
        btn.click()
        