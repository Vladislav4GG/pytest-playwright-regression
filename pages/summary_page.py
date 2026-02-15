# pages/summary_page.py
import re
import time
from playwright.sync_api import expect, Page, TimeoutError as PWTimeoutError

KLARNA_URL_RE = re.compile(r".*klarna\.com.*", re.I)

class SummaryPage:
    def __init__(self, page: Page):
        self.page = page

    def accept_terms(self):
        cb = self.page.locator("#terms-conditions-check-hidden-xs")
        expect(cb).to_be_visible()
        cb.check()

    def _find_place_order_button(self):
        p = self.page

        # Найстабільніше: по тексту
        candidates = [
            p.locator("button:has-text('Place order')"),
            p.locator("button:has-text('PLACE ORDER')"),
            p.get_by_role("button", name=re.compile(r"place\s*order", re.I)),
        ]

        for loc in candidates:
            if loc.count() > 0:
                return loc.first

        # fallback
        return p.locator("button").filter(has_text=re.compile(r"place\s*order", re.I)).first

    def click_paypal_and_wait_page(self, *, timeout: int = 60000) -> Page:
        iframe_sel = "iframe[title='PayPal-paypal'].component-frame.visible"
        iframe = self.page.locator(iframe_sel).first
        iframe.wait_for(state="visible", timeout=timeout)

        paypal_frame = self.page.frame_locator(iframe_sel)
        btn = paypal_frame.locator(
            "[aria-label='PayPal'], [role='link'][aria-label='PayPal'], button[aria-label*='PayPal']"
        ).first
        btn.wait_for(state="visible", timeout=timeout)

        with self.page.expect_popup(timeout=timeout) as pop:
            btn.click(force=True)

        popup = pop.value
        popup.wait_for_load_state("domcontentloaded")
        return popup

    def click_klarna_and_wait_page(self, *, timeout: int = 60000) -> Page:
        """
        Klarna відкривається редіректом у тій же вкладці.
        """
        btn = self._find_place_order_button()
        expect(btn).to_be_visible(timeout=timeout)
        expect(btn).to_be_enabled(timeout=timeout)

        start_url = self.page.url

        btn.click(force=True)

        deadline = time.time() + timeout / 1000
        last_url = self.page.url

        while time.time() < deadline:
            last_url = self.page.url or ""
            if KLARNA_URL_RE.match(last_url) and last_url != start_url:
                self.page.wait_for_load_state("domcontentloaded")
                return self.page
            time.sleep(0.2)

        raise AssertionError(f"Did not redirect to Klarna after Place order. last_url={last_url}")