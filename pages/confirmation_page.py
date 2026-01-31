import re
from playwright.sync_api import Page, expect


# Найчастіший формат у тебе: GB03677003 (GB + 8 цифр)
ORDER_CODE_RE = re.compile(r"\b([A-Z]{2}\d{8})\b")
# Додатковий fallback, якщо раптом інший формат
ORDER_CODE_GENERIC_RE = re.compile(r"\b([A-Z]{2}\d{6,12})\b")


class ConfirmationPage:
    def __init__(self, page: Page):
        self.page = page

    def wait_loaded(self):
        # confirmation сторінка інколи догружає блоки JS-ом,
        # тому краще чекати хоч якийсь "Order confirmation" хедер/секцію.
        # Якщо у вас інший текст — не страшно, тоді просто дочекаємось load + body.
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.locator("body")).to_be_visible(timeout=20000)

    def _extract_from_href(self, href: str) -> str | None:
        if not href:
            return None
        m = ORDER_CODE_RE.search(href) or ORDER_CODE_GENERIC_RE.search(href)
        return m.group(1) if m else None

    def get_order_code(self) -> str:
        self.wait_loaded()

        # 1) Найнадійніше: якщо на confirmation є лінк на order details
        # типу /en_GB/customer/order/GB03677003/...
        link = self.page.locator("a[href*='/customer/order/']").first
        if link.count() > 0:
            href = link.get_attribute("href") or ""
            code = self._extract_from_href(href)
            if code:
                return code

        # 2) Спроба знайти в будь-якому href на сторінці (інколи це кнопки/лінки без тексту)
        hrefs = self.page.locator("a[href]").all()
        for a in hrefs:
            href = a.get_attribute("href") or ""
            code = self._extract_from_href(href)
            if code:
                return code

        # 3) Fallback: пошук у видимому тексті
        try:
            text = self.page.locator("body").inner_text(timeout=5000)
            m = ORDER_CODE_RE.search(text) or ORDER_CODE_GENERIC_RE.search(text)
            if m:
                return m.group(1)
        except Exception:
            pass

        # 4) Fallback: пошук у HTML (сюди потрапляють script/json, data-атрибути, приховані шматки)
        html = self.page.content()
        m = ORDER_CODE_RE.search(html) or ORDER_CODE_GENERIC_RE.search(html)
        if m:
            return m.group(1)

        # 5) Якщо не знайшли — збережемо діагностику, щоб не гадати
        # (це не ламає тест, просто допомагає зрозуміти, що реально на сторінці)
        try:
            self.page.screenshot(path="artifacts/confirmation_debug.png", full_page=True)
        except Exception:
            pass

        try:
            with open("artifacts/confirmation_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

        raise AssertionError(
            "Order code not found on confirmation page. "
            "Saved artifacts/confirmation_debug.html and artifacts/confirmation_debug.png"
        )
    
    def get_first_sku(self) -> str:
        skus = self.get_skus()
        if not skus:
            raise AssertionError("SKU not found on confirmation page.")
        return skus[0]

    def get_skus(self) -> list[str]:
        """
        Якщо треба SKU зі сторінки confirmation:
        шукаємо по тексту 'SKU:' як у твоєму HTML з order overview.
        """
        self.wait_loaded()

        # приклад з твого HTML: <span ...>SKU:</span> <span ...>C13T03R640</span>
        # беремо всі значення SKU зі сторінки
        sku_values = self.page.locator(
            "xpath=//span[contains(normalize-space(.),'SKU')]/following-sibling::span[1]"
        )
        out: list[str] = []
        for i in range(sku_values.count()):
            val = (sku_values.nth(i).inner_text() or "").strip()
            if val:
                out.append(val)

        # fallback: якщо немає такого DOM, пробуємо regex по HTML
        if not out:
            html = self.page.content()
            # простий SKU pattern: букви+цифри, починається з C13... у вас часто так
            m = re.findall(r"\b(C\d{2}[A-Z0-9]{6,})\b", html)
            out = list(dict.fromkeys(m))  # unique order-preserving

        return out