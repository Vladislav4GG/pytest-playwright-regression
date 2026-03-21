from __future__ import annotations

import os

import allure
import pytest

from flows.plp_checks_flow import PlpChecksConfig, PlpChecksFlow

SUCCESS_MESSAGE = "PLP checks completed"


def _test_env() -> str:
    raw = os.getenv("TEST_ENV", "S1").strip().upper()
    return "S2" if raw == "S2" else "S1"


def _plp_url() -> str:
    explicit = os.getenv("PLP_CHECKS_URL", "").strip()
    if explicit:
        return explicit

    base = os.getenv("UI_BASE_URL", "").strip().rstrip("/")
    if base:
        if base.endswith("/en_GB"):
            root = base
        else:
            root = f"{base}/en_GB"
    else:
        suffix = "s2" if _test_env() == "S2" else "s1"
        root = f"https://epson-gb.cbnd-seikoepso3-{suffix}-public.model-t.cc.commerce.ondemand.com/en_GB"

    return f"{root}/products/printers-en-gb/c/printers?q=%3Arelevance&page=0"


def _config() -> PlpChecksConfig:
    max_pages = int(os.getenv("PLP_OPTIONAL_ACTION_SCAN_PAGES", "3"))
    return PlpChecksConfig(
        plp_url=_plp_url(),
        scan_pages_for_optional_actions=max(1, max_pages),
    )


@pytest.mark.functional
@pytest.mark.plp
@allure.title("Functional: PLP checks")
def test_plp_checks(page):
    flow = PlpChecksFlow(page=page, config=_config())
    result = flow.run()

    lines = [SUCCESS_MESSAGE]
    if result.warnings:
        lines.append("warnings:")
        lines.extend(f"- {item}" for item in result.warnings)
        print("[PLP][WARN] Items not found/fully validated:")
        for item in result.warnings:
            print(f"[PLP][WARN] {item}")
    else:
        lines.append("warnings: none")

    allure.attach("\n".join(lines), name="PLP checks result", attachment_type=allure.attachment_type.TEXT)
    print(f"[PLP][PASS] {SUCCESS_MESSAGE}")
