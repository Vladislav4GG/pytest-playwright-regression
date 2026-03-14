from __future__ import annotations

import os
import random
from urllib.parse import urlparse

import allure
import pytest

from pages.site_selector_page import OptionData, SiteSelectorPage
from utils.consent import dismiss_onetrust

SUCCESS_MESSAGE = "Country and locale switching works correctly"
MULTI_LOCALE_COUNTRIES = ("Belgium", "Switzerland", "Europe")


def _base_url() -> str:
    value = os.getenv("UI_BASE_URL", "").strip().rstrip("/")
    if value:
        return f"{value}/en_GB"
    return "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB"


def _rng() -> random.Random:
    raw_seed = os.getenv("SITE_SELECTOR_RANDOM_SEED", "20260312")
    return random.Random(raw_seed)


def _assert_url_matches(url: str, site_code: str, locale_code: str):
    parsed = urlparse(url)
    expected_host_prefix = f"{site_code}."
    if not parsed.netloc.startswith(expected_host_prefix):
        raise AssertionError(
            f"Host mismatch: expected prefix '{expected_host_prefix}', got '{parsed.netloc}'"
        )
    expected_path_prefix = f"/{locale_code}"
    if not parsed.path.startswith(expected_path_prefix):
        raise AssertionError(
            f"Path mismatch: expected prefix '{expected_path_prefix}', got '{parsed.path}'"
        )


def _pick_alternative_language(languages: list[OptionData], current_locale: str) -> OptionData | None:
    for lang in languages:
        if lang["value"] != current_locale:
            return lang
    return None


@pytest.mark.functional
@pytest.mark.locale
@allure.title("Functional: Country and language selector")
def test_country_and_language_switch(page):
    page.goto(_base_url())
    dismiss_onetrust(page)

    selector = SiteSelectorPage(page)
    rng = _rng()

    with allure.step("Check #1: switch to another random country and confirm URL changes"):
        selector.open()
        current_country = selector.selected_country()
        candidates = [c for c in selector.country_options() if c["label"] != current_country["label"]]
        assert candidates, "No alternative countries available in selector"

        target_country = rng.choice(candidates)
        selector.select_country_by_label(target_country["label"])
        target_site_code = selector.selected_country()["value"]
        target_language = selector.selected_language()["value"]

        previous_url = page.url
        selector.confirm_and_wait_for_url_change(previous_url)
        _assert_url_matches(page.url, target_site_code, target_language)

    with allure.step(
        "Check #2: pick Belgium/Switzerland/Europe, choose another language, and confirm URL changes"
    ):
        dismiss_onetrust(page)
        selector.open()

        multi_candidates: list[tuple[OptionData, OptionData]] = []
        for country_name in MULTI_LOCALE_COUNTRIES:
            selector.select_country_by_label(country_name)
            languages = selector.language_options()
            selected_language = selector.selected_language()
            alternative = _pick_alternative_language(languages, selected_language["value"])
            if alternative:
                country = selector.selected_country()
                multi_candidates.append((country, alternative))

        assert multi_candidates, "No multi-locale country with alternative language available"

        target_country, target_language = rng.choice(multi_candidates)
        selector.select_country_by_label(target_country["label"])
        selector.select_language_by_value(target_language["value"])

        previous_url = page.url
        selector.confirm_and_wait_for_url_change(previous_url)
        _assert_url_matches(page.url, target_country["value"], target_language["value"])

    allure.attach(
        SUCCESS_MESSAGE,
        name="Country/Language selector result",
        attachment_type=allure.attachment_type.TEXT,
    )
    print(f"[SITE_SELECTOR][PASS] {SUCCESS_MESSAGE}")
