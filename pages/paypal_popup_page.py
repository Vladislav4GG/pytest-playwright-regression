import re
import time
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PWTimeoutError

class PayPalPopupPage:
    def __init__(self, page: Page):
        self.page = page

    def login_and_approve(self, *, email: str, password: str, timeout: int = 60000):
        p = self.page
        deadline = time.time() + (timeout / 1000)

        # 0) стабілізація
        p.wait_for_load_state("domcontentloaded")
        try:
            p.wait_for_load_state("networkidle", timeout=10_000)
        except PWTimeoutError:
            pass

        # 1) EMAIL step — чекаємо саме VISIBLE інпут
        email_inp = p.locator("input#email, input[name='login_email']").first
        try:
            email_inp.wait_for(state="visible", timeout=timeout)
            email_inp.fill(email)
        except PWTimeoutError:
            # якщо email step вже пройдено/проскочило — ок, йдемо далі
            pass

        # Next після email (якщо є)
        btn_next = p.get_by_role("button", name=re.compile(r"next|continue", re.I)).first
        if btn_next.count() > 0:
            try:
                btn_next.wait_for(state="visible", timeout=5_000)
                btn_next.click()
            except PWTimeoutError:
                pass

        # password step
        pass_inp = self.page.locator("input#password, input[name='login_password']").first
        expect(pass_inp).to_be_visible(timeout=timeout)
        pass_inp.fill(password)

        btn_login = self.page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)).first
        expect(btn_login).to_be_visible(timeout=timeout)
        btn_login.click()

        # 3) Final submit in PayPal: "Complete Purchase"
        complete = self.page.locator(
            "button[data-testid='submit-button-initial'], "
            "button[data-id='payment-submit-btn'], "
            "button:has-text('Complete Purchase')"
        ).first

        complete.wait_for(state="visible", timeout=timeout)
        complete.scroll_into_view_if_needed()
        expect(complete).to_be_enabled(timeout=timeout)
        complete.click()

        # 4) Дочекатись, що popup закрився або змінився URL (без expect.poll)
        while time.time() < deadline:
            try:
                if p.is_closed():
                    return
                url = p.url or ""
                if "checkoutnow" not in url:
                    return
            except Exception:
                return
            time.sleep(0.2)

        raise AssertionError("PayPal popup did not close / did not navigate away after Complete Purchase.")