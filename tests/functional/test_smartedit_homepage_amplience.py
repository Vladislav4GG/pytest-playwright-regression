from __future__ import annotations

import os

import allure
import pytest

from flows.smartedit_amplience_flow import SmartEditAmplienceConfig, SmartEditAmplienceFlow

SUCCESS_MESSAGE = "SmartEdit Amplience component flow works correctly"
COVERED_CASE_IDS = (11,)


def _test_env() -> str:
    raw = os.getenv("TEST_ENV", "S1").strip().upper()
    return "S2" if raw == "S2" else "S1"


def _smartedit_url() -> str:
    explicit = os.getenv("SMARTEDIT_URL", "").strip()
    if explicit:
        return explicit

    suffix = "s2" if _test_env() == "S2" else "s1"
    return f"https://backoffice.cbnd-seikoepso3-{suffix}-public.model-t.cc.commerce.ondemand.com/smartedit/#/"


def _smartedit_credentials() -> tuple[str, str]:
    username = (
        os.getenv("SMARTEDIT_USERNAME", "").strip()
        or os.getenv("CMS_USERNAME", "").strip()
        or "epson_testers_cms"
    )
    password = (
        os.getenv("SMARTEDIT_PASSWORD", "").strip()
        or os.getenv("CMS_PASSWORD", "").strip()
        or "epson123"
    )
    return username, password


def _storefront_page_url(page_name: str) -> str:
    explicit = os.getenv("SMARTEDIT_STOREFRONT_PAGE_URL", "").strip()
    if explicit:
        return explicit

    base = os.getenv("UI_BASE_URL", "").strip().rstrip("/")
    if base:
        if base.endswith("/en_GB"):
            return f"{base}/{page_name}"
        return f"{base}/en_GB/{page_name}"

    suffix = "s2" if _test_env() == "S2" else "s1"
    return f"https://epson-gb.cbnd-seikoepso3-{suffix}-public.model-t.cc.commerce.ondemand.com/en_GB/{page_name}"


def _config() -> SmartEditAmplienceConfig:
    username, password = _smartedit_credentials()
    page_name = os.getenv("SMARTEDIT_PAGE_NAME", "vladampliencepage").strip()

    return SmartEditAmplienceConfig(
        smartedit_url=_smartedit_url(),
        smartedit_username=username,
        smartedit_password=password,
        site_label=os.getenv("SMARTEDIT_SITE_LABEL", "Epson United Kingdom").strip(),
        catalog_label=os.getenv("SMARTEDIT_CATALOG_LABEL", "Epson GB Content Catalog").strip(),
        page_search_query=os.getenv("SMARTEDIT_PAGE_SEARCH_QUERY", "vlad").strip(),
        page_name=page_name,
        storefront_page_url=_storefront_page_url(page_name=page_name),
        target_slot_id=os.getenv("SMARTEDIT_TARGET_SLOT_ID", "Content1Slot-cmsitem_00475000").strip(),
        amplience_slot_id=os.getenv(
            "SMARTEDIT_AMPLIENCE_SLOT_ID",
            "b55e50d0-8195-4945-ad41-5e7e61efc647",
        ).strip(),
        rendered_heading_text=os.getenv("SMARTEDIT_RENDERED_HEADING_TEXT", "Content text HUP+").strip(),
    )


@pytest.mark.functional
@pytest.mark.smartedit
@allure.title("Functional: SmartEdit homepage render and Amplience component interaction")
def test_smartedit_homepage_renders_and_amplience_component_works(page):
    flow = SmartEditAmplienceFlow(page=page, config=_config())

    with allure.step(
        "Create Amplience component in SmartEdit, sync page, verify storefront render, and clean up by removing component"
    ):
        result = flow.run()

    allure.attach(
        (
            f"{SUCCESS_MESSAGE}\n"
            f"component_name={result.component_name}\n"
            f"component_id={result.component_id}\n"
            f"covered_case_ids={','.join(map(str, COVERED_CASE_IDS))}"
        ),
        name="SmartEdit Amplience result",
        attachment_type=allure.attachment_type.TEXT,
    )
    print(f"[SMARTEDIT][PASS] {SUCCESS_MESSAGE}")
    print(f"[SMARTEDIT][INFO] Added and removed component: {result.component_name} ({result.component_id})")
