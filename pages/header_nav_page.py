from __future__ import annotations

import re
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect


class HeaderNavPage:
    SIGN_OUT_SELECTOR = "a[href*='/logout']"
    LOGO_SELECTOR = "a.banner__link[href='/en_GB/']:visible"
    CART_TRIGGER_SELECTOR = (
        ".js-mini-cart-link, "
        ".navigation-top__links-trigger--cart, "
        "a[href='/en_GB/cart']"
    )
    MINI_CART_CHECKOUT_SELECTOR = (
        ".mini-cart a[href*='/cart'], "
        ".js-mini-cart-content a[href*='/cart'], "
        "a[href='/en_GB/cart']"
    )

    def __init__(self, page: Page):
        self.page = page

    @property
    def sign_out_link(self):
        return self.page.locator(self.SIGN_OUT_SELECTOR).first

    def wait_signed_in(self, timeout: int = 15000):
        expect(self.sign_out_link).to_be_visible(timeout=timeout)

    def is_signed_in(self) -> bool:
        return self.sign_out_link.is_visible()

    def sign_out(self, timeout: int = 45000) -> str:
        self.wait_signed_in(timeout=timeout)
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            self.sign_out_link.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self.page.url

    def wait_signed_out(self, timeout: int = 15000):
        expect(self.sign_out_link).to_be_hidden(timeout=timeout)

    def open_basket_and_go_to_cart(self, timeout: int = 45000) -> str:
        start_url = self.page.url
        trigger = self.page.locator(self.CART_TRIGGER_SELECTOR).first
        expect(trigger).to_be_visible(timeout=timeout)
        trigger.click()
        self.page.wait_for_load_state("domcontentloaded")

        if self._is_cart_url(self.page.url):
            return self.page.url

        checkout = self.page.locator(self.MINI_CART_CHECKOUT_SELECTOR).filter(
            has_text=re.compile(r"checkout|cart", re.I)
        ).first

        if checkout.is_visible():
            with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
                checkout.click()
            self.page.wait_for_load_state("domcontentloaded")
            return self.page.url

        # Fallback for environments where mini-cart opens without a visible CTA.
        parts = urlsplit(start_url)
        cart_url = f"{parts.scheme}://{parts.netloc}/en_GB/cart"
        self.page.goto(cart_url, wait_until="domcontentloaded", timeout=timeout)
        return self.page.url

    def go_home_by_logo(self, timeout: int = 45000) -> str:
        logo = self.page.locator(self.LOGO_SELECTOR).first
        expect(logo).to_be_visible(timeout=timeout)
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            logo.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self.page.url

    @staticmethod
    def _is_cart_url(url: str) -> bool:
        return re.search(r"/en_GB/cart(?:$|[/?#])", url) is not None
