# utils/consent.py
from playwright.sync_api import Page

def dismiss_onetrust(page: Page):
    """
    OneTrust інколи не показує кнопку одразу, інколи показує modal/overlay.
    Ми пробуємо кілька шляхів + в крайньому випадку прибираємо overlay через JS.
    """
    try:
        # якщо взагалі є OneTrust на сторінці
        sdk = page.locator("#onetrust-consent-sdk")
        if sdk.count() == 0:
            return

        # 1) найстабільніша кнопка
        btn = page.locator("#onetrust-accept-btn-handler")
        if btn.is_visible():
            btn.click(timeout=2000)
            return

        # 2) інший варіант назви кнопки (інколи)
        accept = page.get_by_role("button", name="Accept All Cookies")
        if accept.is_visible():
            accept.click(timeout=2000)
            return

        # 3) якщо відкритий preferences modal — пробуємо закрити
        close = page.get_by_role("button", name="Close")
        if close.is_visible():
            close.click(timeout=2000)
            return

        # 4) fallback: прибрати оверлей, який перехоплює кліки
        page.evaluate("""
            () => {
              const el = document.querySelector('#onetrust-consent-sdk');
              if (el) el.remove();
              const overlay = document.querySelector('.onetrust-pc-dark-filter');
              if (overlay) overlay.remove();
            }
        """)
    except Exception:
        # якщо банера нема/не встиг — просто йдемо далі
        pass