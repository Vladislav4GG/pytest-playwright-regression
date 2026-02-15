# pages/summary_page.py
import re
import time
from playwright.sync_api import expect, Page, TimeoutError as PWTimeoutError

KLARNA_URL_RE = re.compile(r".*klarna\.com.*", re.I)


class SummaryPage:
    def __init__(self, page: Page):
        self.page = page

    def accept_terms(self, timeout: int = 20000):
        """
        Terms checkbox інколи під оверлеєм/анімацією.
        Робимо видимість + force check.
        """
        cb = self.page.locator("#terms-conditions-check-hidden-xs").first
        expect(cb).to_be_visible(timeout=timeout)
        cb.check(force=True)

    def _find_place_order_button(self):
        """
        На summary це "Place order" (в т.ч. для Klarna).
        Стараємось знайти максимально стабільно.
        """
        p = self.page

        # 1) role=button по accessible name
        by_role = p.get_by_role("button", name=re.compile(r"^\s*place\s*order\s*$", re.I)).first
        if by_role.count() > 0:
            return by_role

        # 2) конкретний текст в кнопці
        by_text = p.locator("button:has-text('Place order')").first
        if by_text.count() > 0:
            return by_text

        # 3) fallback — будь-яка кнопка з place order
        return p.locator("button").filter(has_text=re.compile(r"place\s*order", re.I)).first

    def place_order(self, *, timeout: int = 60000):
        """
        Використовується для Card flow.
        Просто тисне Place order і чекає, що сторінка почне рухатися далі.
        (Не прив’язуємося до конкретного URL, бо у вас різні payment флоу.)
        """
        btn = self._find_place_order_button()
        expect(btn).to_be_visible(timeout=timeout)
        expect(btn).to_be_enabled(timeout=timeout)

        # інколи кнопка з'являється, але ще "плаває" layout
        self.page.wait_for_timeout(300)
        btn.scroll_into_view_if_needed()

        # тицяємо і даємо навігації стартанути
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                btn.click(force=True)
        except PWTimeoutError:
            # інколи навігація не “офіційна” (XHR), але клік все одно валідний
            btn.click(force=True)
            self.page.wait_for_load_state("domcontentloaded")

    def click_paypal_and_wait_page(self, *, timeout: int = 60000) -> Page:
        """
        PayPal відкриває popup із iframe на summary.
        """
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
        Тиснемо Place order і чекаємо, поки URL стане klarna.*
        """
        btn = self._find_place_order_button()
        expect(btn).to_be_visible(timeout=timeout)
        expect(btn).to_be_enabled(timeout=timeout)

        start_url = self.page.url or ""
        btn.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)

        # Клік і чек редіректу
        btn.click(force=True)

        deadline = time.time() + (timeout / 1000.0)
        last_url = self.page.url or ""

        while time.time() < deadline:
            last_url = self.page.url or ""
            if last_url != start_url and KLARNA_URL_RE.search(last_url):
                self.page.wait_for_load_state("domcontentloaded")
                return self.page
            time.sleep(0.2)

        raise AssertionError(f"Did not redirect to Klarna after Place order. last_url={last_url}")