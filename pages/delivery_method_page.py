from playwright.sync_api import Page, expect

class DeliveryMethodPage:
    def __init__(self, page: Page):
        self.page = page

    def next(self):
        btn = self.page.get_by_role("button", name="Next")
        expect(btn).to_be_visible()
        btn.click()