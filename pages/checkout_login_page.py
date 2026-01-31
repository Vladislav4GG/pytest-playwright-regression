from playwright.sync_api import Page, expect

class CheckoutLoginPage:
    def __init__(self, page: Page):
        self.page = page

    def checkout_as_guest(self, email: str):
        email_input = self.page.locator("#guest\\.email")
        expect(email_input).to_be_visible()
        email_input.fill(email)

        # Кнопка може називатись по-різному; пробуємо роль/текст
        guest_btn = self.page.get_by_role("button", name="Check Out as a Guest")
        expect(guest_btn).to_be_visible()
        guest_btn.click()