# pages/checkout_login_page.py
import re
from playwright.sync_api import Page, expect

class CheckoutLoginPage:
    def __init__(self, page: Page):
        self.page = page

    def login(self, *, email: str, password: str, timeout: int = 30000) -> None:
        form = self.page.locator("form#loginForm")
        expect(form).to_be_visible(timeout=timeout)

        email_inp = form.locator("#j_username")
        pwd_inp = form.locator("#j_password")

        expect(email_inp).to_be_visible(timeout=timeout)
        email_inp.fill(email)

        expect(pwd_inp).to_be_visible(timeout=timeout)
        pwd_inp.fill(password)

        submit = form.get_by_role("button", name=re.compile(r"^\s*Sign In and Check Out\s*$", re.I))
        expect(submit).to_be_enabled(timeout=timeout)

        # Важливо: чекаємо навігацію, бо це submit форми
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
            submit.click()

    def checkout_as_guest(self, email: str, timeout: int = 30000):
        # ми точно на checkout login
        expect(self.page).to_have_url(re.compile(r".*/login/checkout.*"), timeout=timeout)

        # ✅ guest email (у тебе: <input id="guest.email" name="email" type="text">)
        email_input = self.page.locator("#guest\\.email").first
        if email_input.count() == 0:
            email_input = self.page.locator("input[name='email']#guest\\.email").first
        if email_input.count() == 0:
            # останній fallback на випадок дрібних змін
            email_input = self.page.locator("input[name='email']").first

        expect(email_input).to_be_visible(timeout=timeout)
        email_input.fill(email)

        # ✅ кнопка "Check Out as a Guest"
        btn = self.page.get_by_role("button", name=re.compile(r"check\s*out\s*as\s*a\s*guest", re.I))
        if btn.count() == 0:
            btn = self.page.locator("button.btn.btn-primary[type='submit']").filter(
                has_text=re.compile(r"check\s*out\s*as\s*a\s*guest", re.I)
            )

        expect(btn.first).to_be_enabled(timeout=timeout)
        btn.first.click()