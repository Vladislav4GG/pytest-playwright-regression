# pages/pdp_page.py
from playwright.sync_api import Page, expect
from utils.consent import dismiss_onetrust

class PDPPage:
    def __init__(self, page: Page):
        self.page = page

    def buy_now(self):
        btn = self.page.locator("button.js-buy-now").first
        expect(btn).to_be_visible()

        # 1-а спроба
        dismiss_onetrust(self.page)
        try:
            btn.click(timeout=5000)
            return
        except Exception:
            # якщо overlay виліз — прибираємо і тиснемо ще раз
            dismiss_onetrust(self.page)
            btn.click(timeout=5000, force=True)