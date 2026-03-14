from __future__ import annotations

from typing import TypedDict

from playwright.sync_api import Page, expect


class OptionData(TypedDict):
    label: str
    value: str


class SiteSelectorPage:
    TRIGGER_SELECTOR = ".js-site-selector-trigger"
    FORM_SELECTOR = "form.js-site-selector-form"
    COUNTRY_SELECTOR = "#siteSelectorCountrydesktop"
    LANGUAGE_SELECTOR = "#siteSelectorLangdesktop"
    CONFIRM_SELECTOR = (
        "form.js-site-selector-form button[type='submit'], "
        "form.js-site-selector-form button:has-text('Confirm')"
    )

    def __init__(self, page: Page):
        self.page = page

    @property
    def trigger(self):
        return self.page.locator(self.TRIGGER_SELECTOR).first

    @property
    def form(self):
        return self.page.locator(self.FORM_SELECTOR).first

    @property
    def country_select(self):
        return self.page.locator(self.COUNTRY_SELECTOR).first

    @property
    def language_select(self):
        return self.page.locator(self.LANGUAGE_SELECTOR).first

    @property
    def confirm_button(self):
        return self.page.locator(self.CONFIRM_SELECTOR).first

    def open(self, timeout: int = 15000):
        if self.form.is_visible():
            return
        expect(self.trigger).to_be_visible(timeout=timeout)
        self.trigger.click()
        expect(self.form).to_be_visible(timeout=timeout)
        expect(self.country_select).to_be_visible(timeout=timeout)
        expect(self.language_select).to_be_visible(timeout=timeout)

    def _selected_option(self, selector: str) -> OptionData:
        result = self.page.evaluate(
            """
            (sel) => {
              const el = document.querySelector(sel);
              if (!el) return null;
              const option = el.options[el.selectedIndex];
              return {
                label: (option?.textContent || '').trim(),
                value: option?.value || '',
              };
            }
            """,
            selector,
        )
        if not result:
            raise AssertionError(f"Select element not found: {selector}")
        return result

    def _options(self, selector: str) -> list[OptionData]:
        options = self.page.evaluate(
            """
            (sel) => {
              const el = document.querySelector(sel);
              if (!el) return [];
              return Array.from(el.options).map((opt) => ({
                label: (opt.textContent || '').trim(),
                value: opt.value || '',
              }));
            }
            """,
            selector,
        )
        return options or []

    def selected_country(self) -> OptionData:
        return self._selected_option(self.COUNTRY_SELECTOR)

    def selected_language(self) -> OptionData:
        return self._selected_option(self.LANGUAGE_SELECTOR)

    def country_options(self) -> list[OptionData]:
        return self._options(self.COUNTRY_SELECTOR)

    def language_options(self) -> list[OptionData]:
        return self._options(self.LANGUAGE_SELECTOR)

    def select_country_by_label(self, label: str):
        self.page.select_option(self.COUNTRY_SELECTOR, label=label)
        self.page.wait_for_timeout(200)

    def select_language_by_label(self, label: str):
        self.page.select_option(self.LANGUAGE_SELECTOR, label=label)
        self.page.wait_for_timeout(150)

    def select_language_by_value(self, value: str):
        self.page.select_option(self.LANGUAGE_SELECTOR, value=value)
        self.page.wait_for_timeout(150)

    def confirm_and_wait_for_url_change(self, previous_url: str, timeout: int = 45000):
        expect(self.confirm_button).to_be_visible(timeout=timeout)
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            self.confirm_button.click()

        self.page.wait_for_load_state("domcontentloaded")
        if self.page.url == previous_url:
            raise AssertionError(f"URL did not change after confirm. url={self.page.url}")
