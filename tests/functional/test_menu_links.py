from __future__ import annotations

import os

import allure
import pytest

from flows.menu_links_flow import MenuLinkFailure, MenuLinksFlow

SUCCESS_MESSAGE = "All menu parent/child/sub-child links were opened successfully"
COVERED_CASE_IDS = (10,)


def _base_url() -> str:
    for key in ("UI_BASE_URL", "BASE_URL", "HOME_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if not value:
            continue
        if value.endswith("/en_GB"):
            return value[: -len("/en_GB")]
        return value
    return "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com"


def _links_limit() -> int:
    raw = os.getenv("MENU_LINKS_LIMIT", "").strip()
    if not raw:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return 0
    return max(value, 0)


def _format_failures(failures: list[MenuLinkFailure]) -> str:
    lines: list[str] = []
    for failure in failures:
        lines.append(
            " | ".join(
                [
                    f"level={failure.level}",
                    f"label={failure.label}",
                    f"requested={failure.requested_url}",
                    f"final={failure.final_url or '<none>'}",
                    f"status={failure.status_code}",
                    f"reasons={','.join(failure.reasons)}",
                ]
            )
        )
    return "\n".join(lines)


@pytest.mark.functional
@allure.title("Functional: menu links do not open 404/server-error pages")
def test_menu_links_open_without_404_or_home_redirect(page):
    flow = MenuLinksFlow(page=page, base_url=_base_url())

    with allure.step("Collect all parent/child/sub-child menu links"):
        links = flow.open_home_and_collect_links()
        assert links, "No menu links were found in header navigation"

        limit = _links_limit()
        if limit > 0 and len(links) > limit:
            links = links[:limit]
            print(f"[MENU][INFO] MENU_LINKS_LIMIT={limit}; running a subset of links")

        print(f"[MENU][INFO] Total links to validate: {len(links)}")

    with allure.step("Open each menu link and collect broken pages without stopping test"):
        failures = flow.validate_links(links)

    if failures:
        report = _format_failures(failures)
        print(f"[MENU][FAIL] Broken links found: {len(failures)}")
        print(report)
        allure.attach(report, name="Broken menu links report", attachment_type=allure.attachment_type.TEXT)
    else:
        print(f"[MENU][PASS] {SUCCESS_MESSAGE}")
        allure.attach(SUCCESS_MESSAGE, name="Menu links result", attachment_type=allure.attachment_type.TEXT)

    assert not failures, (
        f"Found {len(failures)} broken menu links. See test logs and allure attachment for full list. "
        f"covered_case_ids={','.join(map(str, COVERED_CASE_IDS))}"
    )
