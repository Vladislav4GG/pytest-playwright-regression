import re
from playwright.sync_api import Page, expect


class OrderDetailsPage:
    def __init__(self, page: Page):
        self.page = page

    def wait_loaded(self):
        # IMPORTANT: avoid strict mode violation by asserting on a single locator
        container = self.page.locator(".order-overview__sections")
        try:
            expect(container).to_be_visible(timeout=30000)
            return
        except Exception:
            # fallback: in case markup differs on some envs/templates
            expect(self.page.locator(".order-summary").first).to_be_visible(timeout=30000)

    def get_first_sku(self) -> str:
        self.wait_loaded()
        sku_value = self.page.locator(".order-entry__product-sku .order-attribute__value").first
        expect(sku_value).to_be_visible(timeout=20000)
        return sku_value.inner_text().strip()

    def click_return_order(self):
        self.wait_loaded()

        # Prefer exact href pattern if present (most stable)
        # Example: /en_GB/customer/order/GB03677003/returns
        link = self.page.locator("a.btn.btn-primary[href*='/returns']").filter(
            has_text=re.compile(r"^\s*Return Order\s*$", re.I)
        )
        if link.count() > 0 and link.first.is_visible():
            link.first.scroll_into_view_if_needed()
            link.first.click()
            return

        # Role-based fallback
        btn = self.page.get_by_role("link", name=re.compile(r"^\s*Return Order\s*$", re.I))
        if btn.count() > 0 and btn.first.is_visible():
            btn.first.scroll_into_view_if_needed()
            btn.first.click()
            return

        # Text+class fallback
        btn2 = self.page.locator("a.btn.btn-primary").filter(has_text=re.compile(r"Return Order", re.I))
        if btn2.count() > 0 and btn2.first.is_visible():
            btn2.first.scroll_into_view_if_needed()
            btn2.first.click()
            return

        raise AssertionError("Return Order button not found on order details page.")