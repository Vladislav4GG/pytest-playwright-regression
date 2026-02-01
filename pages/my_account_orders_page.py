import re
from playwright.sync_api import Page, expect

class MyAccountOrdersPage:
    URL = "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/my-account/orders"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.URL, wait_until="domcontentloaded", timeout=45000)

        # простий sanity: сторінка повинна мати order history
        expect(self.page.locator("a.order-history__order-id").first).to_be_visible(timeout=20000)

    def open_order_by_code(self, order_code: str, timeout: int = 20000) -> bool:
        """
        Повертає True якщо знайшли order у списку і клікнули.
        False якщо не знайшли (тоді роби fallback на прямий URL).
        """
        link = self.page.locator("a.order-history__order-id", has_text=re.compile(rf"\b{re.escape(order_code)}\b")).first
        if link.count() == 0:
            return False

        expect(link).to_be_visible(timeout=timeout)
        link.scroll_into_view_if_needed()
        link.click(force=True)
        return True