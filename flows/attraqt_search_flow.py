from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.sync_api import Page

from pages.attraqt_search_page import AttraqtSearchPage
from pages.plp_checks_page import PlpChecksPage


@dataclass(frozen=True)
class AttraqtSearchConfig:
    home_url: str
    search_term: str
    filters_url: str


@dataclass(frozen=True)
class AttraqtSearchResult:
    keyword_clicked: str
    keyword_plp_url: str
    product_clicked: str
    product_pdp_url: str
    warnings: tuple[str, ...]


class AttraqtSearchFlow:
    def __init__(self, page: Page, config: AttraqtSearchConfig):
        self.page = page
        self.config = config
        self.search = AttraqtSearchPage(page)
        self.plp = PlpChecksPage(page)

    def run(self) -> AttraqtSearchResult:
        cfg = self.config
        warnings: list[str] = []

        print("[ATTRAQT][STEP] Open homepage and search panel")
        self.search.open_home(cfg.home_url)
        self.search.open_search()

        print(f"[ATTRAQT][STEP] Type search term: {cfg.search_term}")
        self.search.fill_search_term(cfg.search_term)

        keywords: list[str] = []
        products = []
        for _ in range(8):
            keywords = self.search.keyword_suggestions()
            products = self.search.product_suggestions()
            if keywords and products:
                break
            self.page.wait_for_timeout(700)
        assert keywords, "No keyword suggestions displayed in Attraqt left panel"
        assert products, "No product suggestions displayed in Attraqt right panel"

        if not any("eco" in item.lower() or "et" in item.lower() for item in keywords):
            warnings.append("Keyword suggestions were found, but none looked similar to the search phrase.")

        print("[ATTRAQT][STEP] Click keyword suggestion and verify PLP")
        keyword_clicked, keyword_plp_url = self.search.click_first_keyword_suggestion()
        assert AttraqtSearchPage.looks_like_plp(keyword_plp_url), (
            f"Keyword suggestion did not open PLP-like page. url={keyword_plp_url}"
        )

        print("[ATTRAQT][STEP] Re-open search, press Enter, and verify PLP")
        self.search.open_home(cfg.home_url)
        self.search.open_search()
        self.search.fill_search_term(cfg.search_term)
        enter_plp_url = self.search.submit_search()
        if not AttraqtSearchPage.looks_like_plp(enter_plp_url):
            warnings.append(f"Search submit with Enter did not look like PLP url={enter_plp_url}")

        print("[ATTRAQT][STEP] Re-open search, click product suggestion, and verify PDP")
        self.search.open_home(cfg.home_url)
        self.search.open_search()
        self.search.fill_search_term(cfg.search_term)
        product_clicked, product_pdp_url = self.search.click_first_product_suggestion()
        assert AttraqtSearchPage.looks_like_pdp(product_pdp_url), (
            f"Product suggestion did not open PDP-like page. url={product_pdp_url}"
        )

        print("[ATTRAQT][STEP] Validate 3rd/2nd/1st breadcrumb navigation from PDP")
        for level in (3, 2, 1):
            self.page.goto(product_pdp_url, wait_until="domcontentloaded")
            label, expected_href, final_url = self.search.click_breadcrumb_level_from_current(level)
            print(
                f"[ATTRAQT][BREADCRUMB] level={level} label='{label}' expected='{expected_href}' final='{final_url}'"
            )
            expected_path = urlsplit(expected_href).path if expected_href else ""
            final_path = urlsplit(final_url).path
            if expected_path and not final_path.startswith(expected_path):
                warnings.append(
                    f"Breadcrumb level {level} clicked but final URL differs. expected={expected_href} final={final_url}"
                )

        print("[ATTRAQT][STEP] Open filters PLP and validate facets/apply/remove/reset")
        self.plp.open(cfg.filters_url)
        checkbox_count = self.plp.checkbox_filter_count()
        radio_count = self.plp.radio_filter_count()
        range_count = self.plp.range_or_input_filter_count()
        print(
            f"[ATTRAQT][FACETS] checkbox={checkbox_count} radio={radio_count} range_or_input={range_count}"
        )

        if radio_count == 0:
            warnings.append("No radio filters found on PLP.")
        if range_count == 0:
            warnings.append("No slider/input-box filters found on PLP.")

        # Facet scenario A: apply 1 filter, then clear all.
        selected_for_clear = self.plp.apply_checkbox_filters(max_filters=1)
        assert selected_for_clear, "Could not apply any checkbox filter on PLP"
        print(f"[ATTRAQT][FACETS] Applied filter for clear-all scenario: {selected_for_clear}")

        cleared = self.plp.click_clear_all_or_reset()
        if not cleared:
            warnings.append("Clear All/Reset button was not found after applying filter.")
        else:
            print("[ATTRAQT][FACETS] Clicked Clear All/Reset")

        # Facet scenario B: apply filter again, then remove manually from applied filters panel.
        selected_for_remove = self.plp.apply_checkbox_filters(max_filters=1)
        if not selected_for_remove:
            warnings.append("Could not apply filter for manual-remove scenario.")
        else:
            print(f"[ATTRAQT][FACETS] Applied filter for remove scenario: {selected_for_remove}")
            removed = self.plp.remove_selected_filters_via_panel(max_remove=1)
            if removed == 0:
                warnings.append("Could not remove selected filter from the left panel.")
            else:
                print(f"[ATTRAQT][FACETS] Removed filters count: {removed}")

        return AttraqtSearchResult(
            keyword_clicked=keyword_clicked,
            keyword_plp_url=keyword_plp_url,
            product_clicked=product_clicked,
            product_pdp_url=product_pdp_url,
            warnings=tuple(warnings),
        )
