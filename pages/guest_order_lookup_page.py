from playwright.sync_api import Page, expect


class GuestOrderLookupPage:
    URL = "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/guest/order"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.URL)
        form = self.page.locator("#epsonGuestReturnForm")
        expect(form).to_be_visible(timeout=20000)
        return form

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