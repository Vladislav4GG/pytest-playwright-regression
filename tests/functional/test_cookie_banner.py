import os
import pytest
import allure
from playwright.sync_api import expect

from pages.cookie_banner_page import CookieBannerPage

SUCCESS_MESSAGE = "Cookie management works correctly"


def _home_url() -> str:
    for key in ("BASE_URL", "UI_BASE_URL", "HOME_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if not value:
            continue
        if value.endswith("/en_GB"):
            return value
        return f"{value}/en_GB"

    return "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB"


@pytest.mark.functional
@pytest.mark.cookie
@allure.title("Functional: Cookie management (Accept All + Settings Confirm)")
def test_cookie_management_accept_and_confirm(page):
    page.goto(_home_url())
    cookie = CookieBannerPage(page)

    with allure.step("Check #1: click Accept All Cookies and verify banner is closed"):
        cookie.accept_all()
        expect(cookie.banner).to_be_hidden()

    with allure.step("Check #2: open settings, toggle cookie option, confirm, and close modal"):
        cookie.reset_consent_state()
        page.reload(wait_until="domcontentloaded")
        cookie.open_settings()
        cookie.set_category("targeting", enabled=False)
        assert cookie.category_enabled("targeting") is False, "Targeting Cookies should be OFF"
        cookie.set_category("targeting", enabled=True)
        assert cookie.category_enabled("targeting") is True, "Targeting Cookies should be ON"
        cookie.confirm_choices()
        expect(cookie.preferences_modal).to_be_hidden()

    allure.attach(SUCCESS_MESSAGE, name="Cookie management result", attachment_type=allure.attachment_type.TEXT)
    print(f"[COOKIE][PASS] {SUCCESS_MESSAGE}")
