from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect

from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class RegistrationUserData:
    first_name: str
    last_name: str
    email: str
    password: str


class AuthPage:
    LOGIN_FORM_SELECTOR = "form#loginForm"
    REGISTER_FORM_SELECTOR = "form#epsonRegisterForm"

    LOGIN_EMAIL_SELECTOR = "#j_username"
    LOGIN_PASSWORD_SELECTOR = "#j_password"

    REGISTER_FIRST_NAME_SELECTOR = "#register\\.firstName"
    REGISTER_LAST_NAME_SELECTOR = "#register\\.lastName"
    REGISTER_EMAIL_SELECTOR = "#register\\.email"
    REGISTER_CONFIRM_EMAIL_SELECTOR = "#register\\.confirmEmail"
    REGISTER_PASSWORD_SELECTOR = "#password"
    REGISTER_CONFIRM_PASSWORD_SELECTOR = "#register\\.checkPwd"
    REGISTER_PERSONAL_RADIO_SELECTOR = "#PERSONAL"
    REGISTER_TERMS_SELECTOR = "#registerChkTermsConditions"

    def __init__(self, page: Page):
        self.page = page

    @property
    def login_form(self):
        return self.page.locator(self.LOGIN_FORM_SELECTOR).first

    @property
    def register_form(self):
        return self.page.locator(self.REGISTER_FORM_SELECTOR).first

    def open_login_page(self, login_url: str, timeout: int = 45000):
        self.page.goto(login_url, wait_until="domcontentloaded", timeout=timeout)
        self.wait_login_form(timeout=timeout)

    def wait_login_form(self, timeout: int = 15000):
        expect(self.login_form).to_be_visible(timeout=timeout)
        expect(self.login_form.locator(self.LOGIN_EMAIL_SELECTOR)).to_be_visible(timeout=timeout)
        expect(self.login_form.locator(self.LOGIN_PASSWORD_SELECTOR)).to_be_visible(timeout=timeout)

    def login(self, email: str, password: str, timeout: int = 45000):
        self.wait_login_form(timeout=timeout)
        self.login_form.locator(self.LOGIN_EMAIL_SELECTOR).fill(email)
        self.login_form.locator(self.LOGIN_PASSWORD_SELECTOR).fill(password)

        submit = self.login_form.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)).first
        expect(submit).to_be_enabled(timeout=timeout)
        dismiss_onetrust(self.page)
        try:
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
                submit.click()
        except PlaywrightError:
            dismiss_onetrust(self.page)
            # OneTrust overlays can still intercept pointer events; fallback to JS click.
            handle = submit.element_handle()
            if not handle:
                raise
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
                self.page.evaluate("(el) => el.click()", handle)
        self.page.wait_for_load_state("domcontentloaded")

    def wait_register_form(self, timeout: int = 15000):
        expect(self.register_form).to_be_visible(timeout=timeout)
        expect(self.register_form.locator(self.REGISTER_FIRST_NAME_SELECTOR)).to_be_visible(timeout=timeout)
        expect(self.register_form.locator(self.REGISTER_EMAIL_SELECTOR)).to_be_visible(timeout=timeout)

    def register_personal_user(self, user: RegistrationUserData, timeout: int = 45000):
        self.wait_register_form(timeout=timeout)
        form = self.register_form

        form.locator(self.REGISTER_FIRST_NAME_SELECTOR).fill(user.first_name)
        form.locator(self.REGISTER_LAST_NAME_SELECTOR).fill(user.last_name)
        form.locator(self.REGISTER_EMAIL_SELECTOR).fill(user.email)
        form.locator(self.REGISTER_CONFIRM_EMAIL_SELECTOR).fill(user.email)
        form.locator(self.REGISTER_PASSWORD_SELECTOR).fill(user.password)
        form.locator(self.REGISTER_CONFIRM_PASSWORD_SELECTOR).fill(user.password)

        personal = form.locator(self.REGISTER_PERSONAL_RADIO_SELECTOR).first
        expect(personal).to_be_visible(timeout=timeout)
        if not personal.is_checked():
            personal.check()

        terms = form.locator(self.REGISTER_TERMS_SELECTOR).first
        expect(terms).to_be_visible(timeout=timeout)
        if not terms.is_checked():
            terms.check()

        submit = form.get_by_role("button", name=re.compile(r"register", re.I)).first
        expect(submit).to_be_enabled(timeout=timeout)
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            submit.click()
        self.page.wait_for_load_state("domcontentloaded")
