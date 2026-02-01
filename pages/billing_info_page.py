from playwright.sync_api import Page, expect

class BillingInfoPage:
    def __init__(self, page: Page):
        self.page = page

    def fill_and_continue_non_business(self, first: str, last: str, line1: str, town: str, postcode: str):
        expect(self.page.locator("#first-name")).to_be_visible()
        self.page.locator("#first-name").fill(first)
        self.page.locator("#last-name").fill(last)

        # Business Customer? -> No
        no_radio = self.page.locator("#business-customer-off")
        expect(no_radio).to_be_visible()
        no_radio.check()

        self.page.locator("#line-1").fill(line1)
        self.page.locator("#town").fill(town)
        self.page.locator("#postcode").fill(postcode)

        btn = self.page.get_by_role("button", name="Save and Continue")
        expect(btn).to_be_visible()
        btn.click()
        self.page.wait_for_timeout(2500)