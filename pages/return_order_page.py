from playwright.sync_api import Page, expect


class ReturnOrderPage:
    def __init__(self, page: Page):
        self.page = page

    def confirm_return_three_steps(self):
        """
        У вас 3 екрани підряд з однаковою кнопкою.
        Робимо до 3 кліків, кожного разу чекаємо, що сторінка оновилась.
        """
        for i in range(3):
            btn = self.page.locator("button.js-return-order-confirm-button").first
            expect(btn).to_be_visible(timeout=30000)
            expect(btn).to_be_enabled(timeout=30000)
            btn.click()
            # після кліку або navigation, або ререндер
            self.page.wait_for_load_state("domcontentloaded")