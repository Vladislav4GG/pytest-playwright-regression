from __future__ import annotations

import os

import allure
import pytest

from flows.social_links_flow import SocialLinkFailure, SocialLinksFlow

SUCCESS_MESSAGE = "All social media links open the correct platform"


def _home_url() -> str:
    for key in ("UI_BASE_URL", "BASE_URL", "HOME_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if not value:
            continue
        if value.endswith("/en_GB"):
            return value
        return f"{value}/en_GB"
    return "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB"


def _format_failures(failures: list[SocialLinkFailure]) -> str:
    lines: list[str] = []
    for failure in failures:
        lines.append(
            " | ".join(
                [
                    f"platform={failure.platform}",
                    f"label={failure.label}",
                    f"requested={failure.requested_url}",
                    f"final={failure.final_url or '<none>'}",
                    f"reason={failure.reason}",
                ]
            )
        )
    return "\n".join(lines)


@pytest.mark.functional
@pytest.mark.social
@allure.title("Functional: social media links open correct platforms")
def test_social_media_links_redirect_to_correct_platform(page):
    flow = SocialLinksFlow(page=page, base_url=_home_url())

    with allure.step("Collect visible social media links from homepage"):
        links = flow.open_home_and_collect_links()
        assert links, "No visible social media links found on homepage"
        print(f"[SOCIAL][INFO] Total social links to validate: {len(links)}")

    with allure.step("Open each social link and verify it redirects to correct platform"):
        failures = flow.validate_links(links)

    if failures:
        report = _format_failures(failures)
        print(f"[SOCIAL][FAIL] Broken social links found: {len(failures)}")
        print(report)
        allure.attach(report, name="Broken social links report", attachment_type=allure.attachment_type.TEXT)
    else:
        print(f"[SOCIAL][PASS] {SUCCESS_MESSAGE}")
        allure.attach(SUCCESS_MESSAGE, name="Social links result", attachment_type=allure.attachment_type.TEXT)

    assert not failures, f"Found {len(failures)} invalid social media redirects. See logs/allure for details."
