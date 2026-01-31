from playwright.sync_api import Page, expect


class ReturnConfirmPage:
    def __init__(self, page: Page):
        self.page = page

    def confirm(self):
        btn = self.page.locator("button.js-return-order-confirm-button")
        expect(btn).to_be_visible()
        expect(btn).to_be_enabled()
        btn.click()