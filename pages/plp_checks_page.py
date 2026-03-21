from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect

from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class ProductCardSnapshot:
    title: str
    has_image: bool
    price_text: str
    has_buy_now: bool
    has_learn_more: bool
    has_find_dealer: bool
    has_request_callback: bool
    has_readyprint: bool
    has_quick_view: bool
    badges: tuple[str, ...]
    in_stock_label: str


class PlpChecksPage:
    def __init__(self, page: Page):
        self.page = page

    def open(self, url: str, timeout: int = 60000):
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except PlaywrightError:
            # Some PLP responses never fire DOMContentLoaded reliably in CI/headless.
            self.page.goto(url, wait_until="commit", timeout=timeout)
            self.page.wait_for_timeout(2500)
        self._stabilize_click_surface()

    def product_cards(self, limit: int = 10) -> list[ProductCardSnapshot]:
        rows = self.page.evaluate(
            """
            (limit) => {
              const cards = Array.from(
                document.querySelectorAll(
                  ".product-card, .product-view, .product-grid__item, .product-listing-item"
                )
              );
              const result = [];
              for (const card of cards) {
                const title =
                  (card.querySelector(".product-card__title, .product-view__name-link, h3, h2")?.textContent || "")
                    .trim();
                if (!title) continue;
                result.push({
                  title,
                  has_image: !!card.querySelector("img"),
                  price_text: (
                    card.querySelector(".price, .product-card__price, [class*='price']")?.textContent || ""
                  ).trim(),
                  has_buy_now: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /buy now/i.test((el.textContent || "").trim())
                  ),
                  has_learn_more: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /learn more/i.test((el.textContent || "").trim())
                  ),
                  has_find_dealer: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /find a dealer/i.test((el.textContent || "").trim())
                  ),
                  has_request_callback: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /request callback/i.test((el.textContent || "").trim())
                  ),
                  has_readyprint: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /readyprint|see how it works/i.test((el.textContent || "").trim())
                  ),
                  has_quick_view: !!Array.from(card.querySelectorAll("a,button")).find((el) =>
                    /quick view/i.test((el.textContent || "").trim())
                  ),
                  badges: Array.from(card.querySelectorAll(".badge, [class*='badge'], [class*='cashback'], [class*='promo']"))
                    .map((el) => (el.textContent || "").trim())
                    .filter(Boolean)
                    .slice(0, 8),
                  in_stock_label: (
                    Array.from(card.querySelectorAll("span,div,p"))
                      .map((el) => (el.textContent || "").trim())
                      .find((txt) => /in stock/i.test(txt)) || ""
                  ),
                });
                if (result.length >= limit) break;
              }
              return result;
            }
            """,
            limit,
        )
        return [
            ProductCardSnapshot(
                title=row["title"],
                has_image=bool(row["has_image"]),
                price_text=row["price_text"],
                has_buy_now=bool(row["has_buy_now"]),
                has_learn_more=bool(row["has_learn_more"]),
                has_find_dealer=bool(row["has_find_dealer"]),
                has_request_callback=bool(row["has_request_callback"]),
                has_readyprint=bool(row["has_readyprint"]),
                has_quick_view=bool(row["has_quick_view"]),
                badges=tuple(row["badges"]),
                in_stock_label=row["in_stock_label"],
            )
            for row in rows
        ]

    def apply_checkbox_filters(self, max_filters: int = 2, timeout: int = 30000) -> list[str]:
        selected_labels: list[str] = []
        selected_facet_keys: set[str] = set()
        checkboxes = self.page.locator(".facet-filters input[type='checkbox'].js-facet-filter")
        total = checkboxes.count()
        for idx in range(total):
            if len(selected_labels) >= max_filters:
                break
            box = checkboxes.nth(idx)
            try:
                if not box.is_visible():
                    continue
                if box.is_checked():
                    continue
            except PlaywrightError:
                continue

            facet_key = self._facet_key_from_data_query(box.get_attribute("data-query"))
            if facet_key and facet_key in selected_facet_keys:
                continue

            label = self._checkbox_label(box) or f"checkbox_{idx}"
            current_url = self.page.url
            self._stabilize_click_surface()
            handle = box.element_handle()
            if not handle:
                continue
            self.page.evaluate("(el) => el.click()", handle)
            self._wait_url_or_dom_change(current_url, timeout=timeout)
            selected_labels.append(label)
            if facet_key:
                selected_facet_keys.add(facet_key)
        return selected_labels

    def checkbox_filter_count(self) -> int:
        return self.page.locator(".facet-filters input[type='checkbox'].js-facet-filter").count()

    def radio_filter_count(self) -> int:
        return self.page.locator(".facet-filters input[type='radio'].js-facet-filter").count()

    def range_or_input_filter_count(self) -> int:
        return self.page.locator(".facet-filters input[type='range'], .facet-filters input[type='number']").count()

    def remove_selected_filters_via_panel(self, max_remove: int = 2, timeout: int = 30000) -> int:
        removed = 0
        pills = self.page.locator("button.applied-filters__pill--filter.js-facet-filter")
        pills_total = pills.count()
        for idx in range(pills_total):
            if removed >= max_remove:
                break
            pill = pills.nth(idx)
            if not pill.is_visible():
                continue
            current_url = self.page.url
            self._stabilize_click_surface()
            try:
                pill.click()
            except PlaywrightError:
                handle = pill.element_handle()
                if not handle:
                    continue
                self.page.evaluate("(el) => el.click()", handle)
            self._wait_url_or_dom_change(current_url, timeout=timeout)
            removed += 1

        if removed > 0:
            return removed

        checked = self.page.locator(".facet-filters input[type='checkbox'].js-facet-filter:checked")
        total = checked.count()
        for idx in range(total):
            if removed >= max_remove:
                break
            box = checked.nth(idx)
            current_url = self.page.url
            self._stabilize_click_surface()
            handle = box.element_handle()
            if not handle:
                continue
            self.page.evaluate("(el) => el.click()", handle)
            self._wait_url_or_dom_change(current_url, timeout=timeout)
            removed += 1
        return removed

    def click_clear_all_or_reset(self, timeout: int = 30000) -> bool:
        clear = self.page.locator("button.applied-filters__cta.js-facet-filter").first
        if clear.count() > 0 and clear.is_visible():
            current_url = self.page.url
            self._stabilize_click_surface()
            try:
                clear.click()
            except PlaywrightError:
                handle = clear.element_handle()
                if not handle:
                    return False
                self.page.evaluate("(el) => el.click()", handle)
            self._wait_url_or_dom_change(current_url, timeout=timeout)
            return True

        clear = self.page.get_by_role("button", name=re.compile(r"clear all|reset", re.I)).first
        if clear.count() == 0:
            clear = self.page.get_by_role("link", name=re.compile(r"clear all|reset", re.I)).first
        if clear.count() == 0 or not clear.is_visible():
            return False
        current_url = self.page.url
        self._stabilize_click_surface()
        clear.click()
        self._wait_url_or_dom_change(current_url, timeout=timeout)
        return True

    def sort_values(self) -> list[str]:
        return self.page.eval_on_selector_all(
            "select[name='sort'] option, select[name*='sort' i] option, #sortBy option, .sort-by option",
            "opts => opts.map(o => (o.value || '').trim()).filter(Boolean)",
        )

    def selected_sort_value(self) -> str:
        selected = self.page.eval_on_selector_all(
            "select[name='sort'] option:checked, select[name*='sort' i] option:checked, #sortBy option:checked, .sort-by option:checked",
            "opts => opts.map(o => (o.value || '').trim()).filter(Boolean)",
        )
        return selected[0] if selected else ""

    def apply_sort_value(self, target_value: str, timeout: int = 30000) -> bool:
        select = self._first_visible_locator("select[name='sort'], select[name*='sort' i], #sortBy, .sort-by select")
        current_url = self.page.url
        self._stabilize_click_surface()
        if select:
            select.select_option(value=target_value)
        else:
            hidden_select = self.page.locator("select[name='sort'], select[name*='sort' i], #sortBy, .sort-by select").first
            if hidden_select.count() == 0:
                return False
            handle = hidden_select.element_handle()
            if not handle:
                return False
            self.page.evaluate(
                """
                (args) => {
                  const el = args.el;
                  const value = args.value;
                  el.value = value;
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                }
                """,
                {"el": handle, "value": target_value},
            )
        self._wait_url_or_dom_change(current_url, timeout=timeout)
        return True

    def click_pagination_next(self, timeout: int = 30000) -> bool:
        next_link = self._first_visible_locator("a.pagination__arrow--next[href]")
        if not next_link:
            next_link = self._first_visible_locator("a[aria-label*='next page' i][href], a[title*='next' i][href]")
        if not next_link:
            return False
        current_url = self.page.url
        self._stabilize_click_surface()
        next_link.click()
        self._wait_url_or_dom_change(current_url, timeout=timeout)
        return True

    def click_pagination_previous(self, timeout: int = 30000) -> bool:
        prev_link = self._first_visible_locator(
            "a.pagination__arrow--previous[href]:not(.pagination__arrow--disabled)"
        )
        if not prev_link:
            prev_link = self._first_visible_locator("a[aria-label*='previous page' i][href], a[title*='previous' i][href]")
        if not prev_link:
            return False
        current_url = self.page.url
        self._stabilize_click_surface()
        prev_link.click()
        self._wait_url_or_dom_change(current_url, timeout=timeout)
        return True

    def click_action(self, action_pattern: str, timeout: int = 30000) -> tuple[bool, str]:
        action = None
        strict_learn_more = False
        if re.search(r"learn\s*more", action_pattern, re.I):
            strict_learn_more = True
            action = self._first_visible_locator(
                "a.product-button--learn-more[href*='/p/'], a.product-button--learn-more[href*='/products/']"
            )
            if not action:
                action = self._first_visible_locator("a.product-button--learn-more")
        elif re.search(r"find\s*a\s*dealer|where\s*to\s*buy", action_pattern, re.I):
            action = self._first_visible_locator(
                "button.icon-link--where-to-buy, a.icon-link--where-to-buy, button.cc-fi-button, a.cc-fi-button"
            )
        elif re.search(r"request\s*a?\s*callback", action_pattern, re.I):
            action = self._first_visible_locator(
                "a.product-button--request-callback, button.product-button--request-callback"
            )
        elif re.search(r"readyprint", action_pattern, re.I):
            action = self._first_visible_locator("a.readyprint-box__cta, a[href*='readyprint' i]")

        if not action and not strict_learn_more:
            action = self._first_visible_text_action(action_pattern)
        if not action:
            return False, self.page.url

        before = self.page.url
        href = action.get_attribute("href") or ""
        self._stabilize_click_surface()
        try:
            with self.page.context.expect_page(timeout=4000) as popup_info:
                action.click(force=True)
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded", timeout=timeout)
            final = popup.url
            popup.close()
            return True, final
        except PlaywrightError:
            if self.page.url != before:
                return True, self.page.url
            self._stabilize_click_surface()
            try:
                action.click(force=True)
            except PlaywrightError:
                handle = action.element_handle()
                if not handle:
                    return False, self.page.url
                self.page.evaluate("(el) => el.click()", handle)

            if not href:
                self.page.wait_for_timeout(1200)
                return True, self.page.url

            self._wait_url_or_dom_change(before, timeout=timeout)
            return True, self.page.url
        except AssertionError:
            if self.page.url != before:
                return True, self.page.url
            return False, self.page.url

    def open_page_number(self, base_url: str, page_number: int, timeout: int = 60000):
        self.open(self._with_page(base_url, page_number), timeout=timeout)

    def quick_view_details_visible(self, timeout: int = 10000) -> tuple[bool, bool]:
        quick = self._first_visible_text_action(r"quick view")
        if not quick:
            return False, False

        before_url = self.page.url
        self._stabilize_click_surface()
        try:
            quick.click(force=True)
        except PlaywrightError:
            self._stabilize_click_surface()
            quick.click(force=True)

        modal = self.page.locator(
            ".modal:visible, [role='dialog']:visible, .quick-view:visible, "
            ".simple-modal--quick-view:visible, .simple-modal-wrapper:visible, .simple-modal__content:visible"
        ).first
        try:
            expect(modal).to_be_visible(timeout=timeout)
            has_buy_box = (
                modal.get_by_role("button", name=re.compile(r"buy now|add to basket|learn more", re.I)).count() > 0
            )

            close = modal.get_by_role("button", name=re.compile(r"close|×|x", re.I)).first
            if close.count() == 0:
                close = self.page.locator("button.simple-modal__close-button:visible").first
            if close.count() > 0 and close.is_visible():
                close.click()
            else:
                self.page.keyboard.press("Escape")
            return True, has_buy_box
        except AssertionError:
            # Some templates route Quick View directly to PDP instead of opening a modal.
            if self.page.url != before_url:
                has_buy_box = (
                    self.page.get_by_role("button", name=re.compile(r"buy now|add to basket|learn more", re.I)).count()
                    > 0
                )
                self.page.go_back(wait_until="domcontentloaded", timeout=timeout)
                return True, has_buy_box
            return False, False

    def page_contains_text(self, pattern: str) -> bool:
        return self.page.get_by_text(re.compile(pattern, re.I)).count() > 0

    def has_strike_through_price(self) -> bool:
        if self.page.locator("s, del, .strike, [class*='strike'], [class*='old-price']").count() > 0:
            return True
        return self.page_contains_text(r"original\s*price")

    def has_currency_symbol(self) -> bool:
        return self.page_contains_text(r"£|€|\$")

    def has_vat_text(self) -> tuple[bool, bool]:
        incl = self.page_contains_text(r"incl\.?\s*vat") or self.page_contains_text(r"vat\s*incl")
        excl = self.page_contains_text(r"ex\.?\s*vat") or self.page_contains_text(r"vat\s*excl")
        return incl, excl

    def has_cashback_badge(self) -> bool:
        return self.page_contains_text(r"cashback")

    @staticmethod
    def _with_page(url: str, page_number: int) -> str:
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["page"] = str(page_number)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    def _checkbox_label(self, box) -> str:
        try:
            label_text = box.evaluate(
                """
                (el) => {
                  const label = el.closest('label') || document.querySelector(`label[for='${el.id}']`);
                  return label ? (label.textContent || '').trim() : '';
                }
                """
            )
            return label_text or ""
        except PlaywrightError:
            return ""

    def _wait_url_or_dom_change(self, previous_url: str, timeout: int = 30000):
        try:
            self.page.wait_for_function(
                "(prev) => window.location.href !== prev",
                arg=previous_url,
                timeout=timeout,
            )
        except PlaywrightError:
            self.page.wait_for_timeout(1500)

    def _first_visible_locator(self, selector: str):
        loc = self.page.locator(selector)
        total = loc.count()
        for idx in range(total):
            item = loc.nth(idx)
            try:
                if item.is_visible():
                    return item
            except PlaywrightError:
                continue
        return None

    def _first_visible_text_action(self, action_pattern: str):
        regex = re.compile(action_pattern, re.I)
        loc = self.page.locator("a,button").filter(has_text=regex)
        total = loc.count()
        for idx in range(total):
            item = loc.nth(idx)
            try:
                if item.is_visible():
                    return item
            except PlaywrightError:
                continue
        return None

    @staticmethod
    def _facet_key_from_data_query(data_query: str | None) -> str:
        if not data_query:
            return ""
        parts = [part for part in data_query.split(":") if part]
        if len(parts) < 3:
            return ""
        # Pattern is typically :relevance:<facet_name>:<facet_value>
        return parts[1].strip().lower()

    def _stabilize_click_surface(self):
        dismiss_onetrust(self.page)
        try:
            self.page.evaluate(
                """
                () => {
                  const selectors = [
                    "#onetrust-consent-sdk",
                    ".onetrust-pc-dark-filter",
                    ".onetrust-modal-backdrop",
                    ".ot-sdk-container",
                    ".ot-sdk-row",
                    "[id^='onetrust-pc-sdk']",
                  ];
                  for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach((node) => node.remove());
                  }
                }
                """
            )
        except PlaywrightError:
            pass
