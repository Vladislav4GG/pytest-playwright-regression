import re
from playwright.sync_api import Page, expect

class OrderDetailsRegisteredPage:
    def __init__(self, page: Page):
        self.page = page

    def wait_loaded(self, timeout: int = 20000):
        # сторінка типу /en_GB/my-account/order/GB....
        expect(self.page).to_have_url(re.compile(r".*/my-account/order/GB\d+"), timeout=timeout)

    def click_return_order(self, timeout: int = 20000):
        btn = self.page.locator("a.btn.btn-primary", has_text=re.compile(r"^\s*Return Order\s*$", re.I)).first
        expect(btn).to_be_visible(timeout=timeout)
        btn.scroll_into_view_if_needed()
        btn.click(force=True)