from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Page

from pages.plp_checks_page import PlpChecksPage


@dataclass(frozen=True)
class PlpChecksConfig:
    plp_url: str
    scan_pages_for_optional_actions: int = 3


@dataclass(frozen=True)
class PlpChecksResult:
    warnings: tuple[str, ...]


class PlpChecksFlow:
    def __init__(self, page: Page, config: PlpChecksConfig):
        self.page = page
        self.config = config
        self.plp = PlpChecksPage(page)

    def run(self) -> PlpChecksResult:
        cfg = self.config
        warnings: list[str] = []

        print("[PLP][STEP] Open PLP")
        self.plp.open(cfg.plp_url)

        cards = self.plp.product_cards(limit=12)
        assert cards, "No product cards found on PLP"

        if not any(card.has_image for card in cards):
            raise AssertionError("No product image found in sampled PLP cards")
        if not any(card.price_text for card in cards):
            raise AssertionError("No product price found in sampled PLP cards")
        if not self.plp.has_currency_symbol():
            raise AssertionError("No currency symbol found on PLP")

        vat_incl, vat_excl = self.plp.has_vat_text()
        if not vat_incl:
            warnings.append("VAT incl text was not found on PLP.")
        if not vat_excl:
            warnings.append("VAT excl text was not found on PLP.")

        if not self.plp.has_strike_through_price():
            warnings.append("No strike-through promotion price was found on current PLP dataset.")

        if not any(card.in_stock_label and card.has_buy_now for card in cards):
            warnings.append("No sampled product card had both 'In stock' and 'Buy Now'.")

        print("[PLP][STEP] Pagination next/previous")
        moved_next = self.plp.click_pagination_next()
        if not moved_next:
            warnings.append("Next page control was not clickable.")
        else:
            moved_prev = self.plp.click_pagination_previous()
            if not moved_prev:
                warnings.append("Previous page control was not clickable.")

        print("[PLP][STEP] Sorting")
        sort_values: list[str] = []
        for _ in range(6):
            sort_values = self.plp.sort_values()
            if sort_values:
                break
            self.page.wait_for_timeout(600)
        selected = self.plp.selected_sort_value()
        preferred_order = ("newest-first", "price-desc", "price-asc")
        target_sort = next((value for value in preferred_order if value in sort_values and value != selected), None)
        if target_sort:
            changed = self.plp.apply_sort_value(target_sort)
            if not changed:
                warnings.append(f"Could not apply sort value '{target_sort}'.")
        else:
            warnings.append("No suitable sort option found for Newest/Price checks.")

        print("[PLP][STEP] Learn More")
        clicked, final = self.plp.click_action(r"learn more")
        if not clicked:
            warnings.append("Learn More action was not found.")
        elif not re.search(r"/p/[0-9]+|/p/\\w+", final):
            warnings.append(f"Learn More did not open PDP-like URL: {final}")
        if clicked and self.page.url != cfg.plp_url:
            self.plp.open(cfg.plp_url)

        print("[PLP][STEP] Optional product actions across pages")
        self._find_optional_action(
            "Find a Dealer", r"find a dealer|where to buy", cfg.scan_pages_for_optional_actions, warnings
        )
        self._find_optional_action(
            "Request Callback", r"request a callback|request callback", cfg.scan_pages_for_optional_actions, warnings
        )
        self._find_optional_action(
            "ReadyPrint", r"readyprint|pick your plan|see how it works", cfg.scan_pages_for_optional_actions, warnings
        )

        print("[PLP][STEP] Quick View")
        self.plp.open(cfg.plp_url)
        quick_found, quick_has_buy_box = self.plp.quick_view_details_visible()
        if not quick_found:
            warnings.append("Quick View action was not found.")
        elif not quick_has_buy_box:
            warnings.append("Quick View opened but Buy Box-like actions were not found in modal.")

        if not self.plp.has_cashback_badge():
            warnings.append("No badge/cashback label was detected in sampled PLP products.")

        return PlpChecksResult(warnings=tuple(warnings))

    def _find_optional_action(
        self,
        action_name: str,
        pattern: str,
        max_pages: int,
        warnings: list[str],
    ):
        cfg = self.config
        for page_idx in range(max_pages):
            self.plp.open_page_number(cfg.plp_url, page_idx)
            clicked, final_url = self.plp.click_action(pattern)
            if not clicked:
                continue
            print(f"[PLP][ACTION] {action_name} clicked on page={page_idx} final={final_url}")
            return
        warnings.append(f"{action_name} action was not found within first {max_pages} PLP pages.")
