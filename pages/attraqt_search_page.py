from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Page, expect

from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class ProductSuggestion:
    title: str
    href: str


class AttraqtSearchPage:
    SEARCH_OPEN_BUTTON = (
        "button.js-toggle-xs-search[aria-label='Search'], "
        "button.glyphicon-search, "
        "button.search-icon"
    )
    SEARCH_INPUT = "input.search-panel__search-box-input.js-search-panel-search-box-input"
    KEYWORD_SUGGESTION = "a.search-panel__suggestion"
    PRODUCT_SUGGESTION = "a.search-panel__product-name"

    def __init__(self, page: Page):
        self.page = page

    def open_home(self, url: str, timeout: int = 60000):
        self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        dismiss_onetrust(self.page)

    def open_search(self, timeout: int = 20000):
        trigger = self.page.locator(self.SEARCH_OPEN_BUTTON).first
        expect(trigger).to_be_visible(timeout=timeout)
        trigger.click()
        search_input = self.page.locator(self.SEARCH_INPUT).first
        expect(search_input).to_be_visible(timeout=timeout)

    def fill_search_term(self, term: str, timeout: int = 20000):
        search_input = self.page.locator(self.SEARCH_INPUT).first
        expect(search_input).to_be_visible(timeout=timeout)
        search_input.click()
        search_input.press("ControlOrMeta+A")
        search_input.press("Backspace")
        search_input.type(term, delay=80)

    def submit_search(self, timeout: int = 45000) -> str:
        search_input = self.page.locator(self.SEARCH_INPUT).first
        expect(search_input).to_be_visible(timeout=timeout)
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            search_input.press("Enter")
        return self.page.url

    def keyword_suggestions(self) -> list[str]:
        suggestions = []
        locator = self.page.locator(self.KEYWORD_SUGGESTION)
        for i in range(locator.count()):
            text = locator.nth(i).inner_text().strip()
            if text:
                suggestions.append(text)
        return suggestions

    def product_suggestions(self) -> list[ProductSuggestion]:
        suggestions: list[ProductSuggestion] = []
        locator = self.page.locator(self.PRODUCT_SUGGESTION)
        for i in range(locator.count()):
            item = locator.nth(i)
            text = item.inner_text().strip()
            href = item.get_attribute("href") or ""
            if text and href:
                suggestions.append(ProductSuggestion(title=text, href=href))
        return suggestions

    def click_first_keyword_suggestion(self, timeout: int = 45000) -> tuple[str, str]:
        first = self.page.locator(self.KEYWORD_SUGGESTION).first
        expect(first).to_be_visible(timeout=timeout)
        label = first.inner_text().strip()
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            first.click()
        return label, self.page.url

    def click_first_product_suggestion(self, timeout: int = 45000) -> tuple[str, str]:
        first = self.page.locator(self.PRODUCT_SUGGESTION).first
        expect(first).to_be_visible(timeout=timeout)
        label = first.inner_text().strip()
        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            first.click()
        return label, self.page.url

    def click_breadcrumb_level_from_current(self, level_from_current: int, timeout: int = 45000) -> tuple[str, str, str]:
        links = self.page.locator(".breadcrumb a, .breadcrumbs a, nav[aria-label='breadcrumb'] a")
        count = links.count()
        if count < level_from_current:
            raise AssertionError(
                f"Not enough breadcrumb links for level {level_from_current}. Available={count}"
            )

        index = count - level_from_current
        target = links.nth(index)
        label = target.inner_text().strip()
        expected_href = target.get_attribute("href") or ""

        with self.page.expect_navigation(wait_until="domcontentloaded", timeout=timeout):
            target.click()
        return label, expected_href, self.page.url

    @staticmethod
    def looks_like_plp(url: str) -> bool:
        return bool(re.search(r"/c/|/search/", url))

    @staticmethod
    def looks_like_pdp(url: str) -> bool:
        return bool(re.search(r"/p/[0-9]+|/p/\\w+", url))
