import re
from playwright.sync_api import Page, expect
from utils.consent import dismiss_onetrust

class CartPage:
    def __init__(self, page: Page):
        self.page = page

    def click_checkout(self):
        dismiss_onetrust(self.page)
        expect(self.page).to_have_url(re.compile(r".*/cart.*"))

        btns = self.page.locator("button.js-continue-checkout-button")

        # 1) дочекайся що кнопки зʼявились у DOM
        expect(btns.first).to_be_attached()

        # 2) дочекайся що хоча б одна стала видимою
        expect(btns.first).to_be_visible()

        # 3) клік (strict mode не проблема, бо ми клікаємо конкретно first)
        btns.first.click()