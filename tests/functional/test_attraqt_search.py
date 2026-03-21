from __future__ import annotations

import os

import allure
import pytest

from flows.attraqt_search_flow import AttraqtSearchConfig, AttraqtSearchFlow

SUCCESS_MESSAGE = "Attraqt search scenarios completed"


def _test_env() -> str:
    raw = os.getenv("TEST_ENV", "S1").strip().upper()
    return "S2" if raw == "S2" else "S1"


def _home_url() -> str:
    explicit = os.getenv("UI_BASE_URL", "").strip().rstrip("/")
    if explicit:
        if explicit.endswith("/en_GB"):
            return explicit
        return f"{explicit}/en_GB"
    suffix = "s2" if _test_env() == "S2" else "s1"
    return f"https://epson-gb.cbnd-seikoepso3-{suffix}-public.model-t.cc.commerce.ondemand.com/en_GB"


def _filters_url() -> str:
    explicit = os.getenv("ATTRAQT_FILTERS_URL", "").strip()
    if explicit:
        return explicit
    return f"{_home_url()}/products/printers-en-gb/c/printers"


def _config() -> AttraqtSearchConfig:
    return AttraqtSearchConfig(
        home_url=_home_url(),
        search_term=os.getenv("ATTRAQT_SEARCH_TERM", "Ecotank ET").strip(),
        filters_url=_filters_url(),
    )


@pytest.mark.functional
@pytest.mark.search
@allure.title("Functional: Search via Attraqt")
def test_search_via_attraqt(page):
    flow = AttraqtSearchFlow(page=page, config=_config())
    result = flow.run()

    summary = [
        SUCCESS_MESSAGE,
        f"keyword_clicked={result.keyword_clicked}",
        f"keyword_plp_url={result.keyword_plp_url}",
        f"product_clicked={result.product_clicked}",
        f"product_pdp_url={result.product_pdp_url}",
    ]
    if result.warnings:
        summary.append("warnings:")
        summary.extend(f"- {item}" for item in result.warnings)
        print("[ATTRAQT][WARN] Items not found/fully validated:")
        for item in result.warnings:
            print(f"[ATTRAQT][WARN] {item}")
    else:
        summary.append("warnings: none")

    allure.attach("\n".join(summary), name="Attraqt search result", attachment_type=allure.attachment_type.TEXT)
    print(f"[ATTRAQT][PASS] {SUCCESS_MESSAGE}")
