import os
from playwright.sync_api import Page, expect


class GuestOrderLookupPage:
    def __init__(self, page):
        self.page = page

    def open(self):
        base = os.getenv("UI_BASE_URL")
        if not base:
            raise RuntimeError("UI_BASE_URL is missing")
        self.page.goto(f"{base}/en_GB/guest/order", wait_until="domcontentloaded")

    def retrieve_order(self, email: str, order_code: str):
        form = self.page.locator("#epsonGuestReturnForm")
        expect(form).to_be_visible(timeout=20000)

        email_input = form.locator("#email")
        order_input = form.locator("#orderCode")
        submit_btn = form.get_by_role("button", name="Retrieve Order")

        expect(email_input).to_be_visible()
        expect(order_input).to_be_visible()
        expect(submit_btn).to_be_enabled()

        email_input.fill(email)
        order_input.fill(order_code)
        submit_btn.click()