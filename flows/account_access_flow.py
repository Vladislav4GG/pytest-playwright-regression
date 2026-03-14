from __future__ import annotations

from playwright.sync_api import Page

from pages.auth_page import AuthPage, RegistrationUserData
from pages.cookie_banner_page import CookieBannerPage
from pages.header_nav_page import HeaderNavPage


class AccountAccessFlow:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.home_url = f"{self.base_url}/en_GB"
        self.login_url = f"{self.base_url}/en_GB/login"

        self.cookie = CookieBannerPage(page)
        self.auth = AuthPage(page)
        self.header = HeaderNavPage(page)

    def open_home_and_accept_cookie(self):
        self.page.goto(self.home_url, wait_until="domcontentloaded", timeout=45000)
        self.cookie.accept_all()

    def sign_in_registered_user(self, email: str, password: str) -> str:
        self.auth.open_login_page(self.login_url)
        self.auth.login(email=email, password=password)
        self.header.wait_signed_in()
        return self.page.url

    def sign_out_registered_user(self) -> str:
        url = self.header.sign_out()
        self.header.wait_signed_out()
        return url

    def register_new_user(self, user: RegistrationUserData) -> str:
        self.auth.open_login_page(self.login_url)
        self.auth.register_personal_user(user=user)
        self.header.wait_signed_in()
        return self.page.url

    def open_basket_checkout_to_cart(self) -> str:
        return self.header.open_basket_and_go_to_cart()

    def navigate_home_by_logo(self) -> str:
        return self.header.go_home_by_logo()
