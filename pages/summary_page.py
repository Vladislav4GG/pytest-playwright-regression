# pages/summary_page.py
from playwright.sync_api import Page, expect

class SummaryPage:
    def __init__(self, page: Page):
        self.page = page

    def accept_terms(self):
        cb = self.page.locator("#terms-conditions-check-hidden-xs")
        expect(cb).to_be_visible()
        cb.check()

    def place_order(self):
        btn = self.page.get_by_role("button", name="Place Order")
        expect(btn).to_be_enabled()
        btn.click()