from playwright.sync_api import Page, expect


class GuestOrderPage:
    URL = "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/guest/order"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(self.URL)
        expect(self.page.locator("form")).to_be_visible(timeout=20000)

    def retrieve_order(self, email: str, order_code: str):
        email_inp = self.page.locator("input#email")
        code_inp = self.page.locator("input#orderCode")
        btn = self.page.locator("button[type='submit'].btn--checkout")

        expect(email_inp).to_be_visible()
        email_inp.fill(email)

        expect(code_inp).to_be_visible()
        code_inp.fill(order_code)

        expect(btn).to_be_enabled()
        btn.click()

        self.page.wait_for_load_state("domcontentloaded")