import re
from playwright.sync_api import Page, expect
from utils.consent import dismiss_onetrust

class CartPage:
    def __init__(self, page: Page):
        self.page = page

    def click_checkout(self, timeout: int = 20000):
        dismiss_onetrust(self.page)
        expect(self.page).to_have_url(re.compile(r".*/cart.*"))

        btns = self.page.locator("button.js-continue-checkout-button")
        if btns.count() > 0:
            expect(btns.first).to_be_attached(timeout=timeout)
            expect(btns.first).to_be_visible(timeout=timeout)
            btns.first.click()
            return

        # fallback якщо клас інший
        btn = self.page.locator("button, a").filter(has_text=re.compile(r"checkout|continue|proceed", re.I))
        expect(btn.first).to_be_visible(timeout=timeout)
        btn.first.click()