# pages/payment_method_page.py
from playwright.sync_api import Page, expect

class PaymentMethodPage:
    def __init__(self, page: Page):
        self.page = page

    def select_credit_card(self):
        radio = self.page.locator("#paymentMethod-adyen_card")
        expect(radio).to_be_visible()
        radio.check()

    def fill_card(self, number: str, expiry: str, cvc: str, holder: str):
        # Card number iframe
        card_iframe = self.page.locator('[data-cse="encryptedCardNumber"] iframe')
        exp_iframe  = self.page.locator('[data-cse="encryptedExpiryDate"] iframe')
        cvc_iframe  = self.page.locator('[data-cse="encryptedSecurityCode"] iframe')

        # В кожному securedFields.html поле має "input"
        self.page.frame_locator('[data-cse="encryptedCardNumber"] iframe').locator("input").fill(number)
        self.page.frame_locator('[data-cse="encryptedExpiryDate"] iframe').locator("input").fill(expiry)
        self.page.frame_locator('[data-cse="encryptedSecurityCode"] iframe').locator("input").fill(cvc)

        name = self.page.locator('input[name="holderName"]')
        expect(name).to_be_visible()
        name.fill(holder)

    def click_next(self):
        btn = self.page.get_by_role("button", name="Next")
        expect(btn).to_be_enabled()
        btn.click()