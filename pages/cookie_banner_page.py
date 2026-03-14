from playwright.sync_api import Page, expect


class CookieBannerPage:
    BANNER_SELECTOR = "#onetrust-consent-sdk"
    ACCEPT_ALL_SELECTOR = "#onetrust-accept-btn-handler"
    SETTINGS_SELECTOR = "#onetrust-pc-btn-handler"
    FLOATING_SETTINGS_SELECTOR = ".ot-sdk-show-settings"
    PREFERENCES_MODAL_SELECTOR = "#onetrust-pc-sdk"
    CONFIRM_CHOICES_TEXT = "Confirm My Choices"

    CATEGORY_TOGGLE_SELECTORS = {
        "targeting": "#ot-group-id-C0004",
        "functional": "#ot-group-id-C0003",
        "performance": "#ot-group-id-C0002",
    }
    CONSENT_COOKIES = ("OptanonConsent", "OptanonAlertBoxClosed")
    CONSENT_STORAGE_KEYS = ("OptanonConsent", "OptanonAlertBoxClosed")

    def __init__(self, page: Page):
        self.page = page

    @property
    def accept_all_button(self):
        return self.page.locator(self.ACCEPT_ALL_SELECTOR).first

    @property
    def settings_button(self):
        return self.page.locator(self.SETTINGS_SELECTOR).first

    @property
    def floating_settings_button(self):
        return self.page.locator(self.FLOATING_SETTINGS_SELECTOR).first

    @property
    def preferences_modal(self):
        return self.page.locator(self.PREFERENCES_MODAL_SELECTOR).first

    @property
    def confirm_choices_button(self):
        return self.page.get_by_role("button", name=self.CONFIRM_CHOICES_TEXT).first

    @property
    def banner(self):
        return self.page.locator(self.BANNER_SELECTOR).first

    def wait_banner(self, timeout: int = 15000):
        expect(self.banner).to_be_visible(timeout=timeout)
        expect(self.accept_all_button).to_be_visible(timeout=timeout)

    def reset_consent_state(self):
        self.page.evaluate(
            """
            ({ cookieNames, storageKeys }) => {
              for (const key of storageKeys) {
                window.localStorage.removeItem(key);
                window.sessionStorage.removeItem(key);
              }

              const host = window.location.hostname || "";
              const parts = host.split(".");
              const domains = new Set([host, `.${host}`]);
              for (let i = 0; i < parts.length - 1; i++) {
                const tail = parts.slice(i).join(".");
                domains.add(tail);
                domains.add(`.${tail}`);
              }

              for (const name of cookieNames) {
                document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
                for (const domain of domains) {
                  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; domain=${domain}`;
                }
              }
            }
            """,
            {"cookieNames": self.CONSENT_COOKIES, "storageKeys": self.CONSENT_STORAGE_KEYS},
        )

    def ensure_banner_visible(self, timeout: int = 15000):
        if self.accept_all_button.is_visible():
            return

        self.reset_consent_state()
        self.page.reload(wait_until="domcontentloaded")
        self.wait_banner(timeout=timeout)

    def accept_all(self, timeout: int = 15000):
        self.ensure_banner_visible(timeout=timeout)
        self.accept_all_button.click()
        expect(self.accept_all_button).to_be_hidden(timeout=timeout)
        expect(self.banner).to_be_hidden(timeout=timeout)

    def open_settings(self, timeout: int = 15000):
        if self.settings_button.is_visible():
            self.settings_button.click()
        else:
            self.floating_settings_button.click()
        expect(self.preferences_modal).to_be_visible(timeout=timeout)

    def _category_toggle(self, category: str):
        selector = self.CATEGORY_TOGGLE_SELECTORS.get(category)
        if not selector:
            supported = ", ".join(sorted(self.CATEGORY_TOGGLE_SELECTORS))
            raise ValueError(f"Unknown category '{category}'. Supported: {supported}")
        return self.page.locator(selector).first

    def _category_label(self, category: str):
        selector = self.CATEGORY_TOGGLE_SELECTORS.get(category)
        if not selector:
            supported = ", ".join(sorted(self.CATEGORY_TOGGLE_SELECTORS))
            raise ValueError(f"Unknown category '{category}'. Supported: {supported}")
        input_id = selector.removeprefix("#")
        return self.page.locator(f"label.ot-switch[for='{input_id}']").first

    def set_category(self, category: str, enabled: bool, timeout: int = 15000):
        toggle = self._category_toggle(category)
        label = self._category_label(category)
        expect(label).to_be_visible(timeout=timeout)
        if toggle.is_checked() != enabled:
            label.click()
        expect(toggle).to_have_js_property("checked", enabled)

    def category_enabled(self, category: str, timeout: int = 15000) -> bool:
        toggle = self._category_toggle(category)
        return toggle.is_checked()

    def confirm_choices(self, timeout: int = 15000):
        expect(self.confirm_choices_button).to_be_visible(timeout=timeout)
        self.confirm_choices_button.click()
        expect(self.preferences_modal).to_be_hidden(timeout=timeout)
