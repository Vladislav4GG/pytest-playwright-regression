from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests
from playwright.sync_api import Page

from pages.menu_navigation_page import MenuLink, MenuNavigationPage
from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class MenuLinkFailure:
    level: str
    label: str
    requested_url: str
    final_url: str
    status_code: int | None
    reasons: tuple[str, ...]


class MenuLinksFlow:
    NOT_FOUND_TEXT = "We may have sent a printer into space, but this page is beyond even our reach"
    DEFAULT_WORKERS = 8
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.home_url = f"{self.base_url}/en_GB"
        self.menu = MenuNavigationPage(page)
        self.last_warnings: list[MenuLinkFailure] = []

    def open_home_and_collect_links(self) -> list[MenuLink]:
        self.page.goto(self.home_url, wait_until="domcontentloaded", timeout=45000)
        dismiss_onetrust(self.page)
        return self.menu.collect_internal_links()

    def validate_links(self, links: list[MenuLink], timeout: int = 45000) -> list[MenuLinkFailure]:
        failures: list[MenuLinkFailure] = []
        warnings: list[MenuLinkFailure] = []
        workers = self._workers()
        timeout_s = max(int(timeout / 1000), 10)

        print(f"[MENU][INFO] HTTP parallel check enabled, workers={workers}, timeout_s={timeout_s}")

        for index, link in enumerate(links, start=1):
            print(f"[MENU][CHECK] {index}/{len(links)} [{link.level}] {link.label} -> {link.url}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_link = {
                executor.submit(self._check_link_http, link, timeout_s): link
                for link in links
            }

            for future in as_completed(future_to_link):
                link = future_to_link[future]
                try:
                    failure = future.result()
                except Exception as exc:
                    failure = MenuLinkFailure(
                        level=link.level,
                        label=link.label,
                        requested_url=link.url,
                        final_url=link.url,
                        status_code=None,
                        reasons=(f"worker_error_{exc.__class__.__name__}",),
                    )

                if failure:
                    if all(reason.startswith("http_request_error_") for reason in failure.reasons):
                        warnings.append(failure)
                    else:
                        failures.append(failure)

        failures.sort(key=lambda item: item.requested_url)
        warnings.sort(key=lambda item: item.requested_url)
        self.last_warnings = warnings
        return failures

    def _check_link_http(self, link: MenuLink, timeout_s: int) -> MenuLinkFailure | None:
        reasons: list[str] = []
        status_code: int | None = None
        final_url = link.url

        try:
            response = requests.get(
                link.url,
                allow_redirects=True,
                timeout=timeout_s,
                headers={"User-Agent": self.USER_AGENT},
            )
            status_code = response.status_code
            final_url = response.url
            body = response.text or ""
            body_lower = body.lower()

            if status_code >= 400:
                reasons.append(f"http_status_{status_code}")

            if self._redirected_to_home(link.url, final_url):
                reasons.append("redirected_to_homepage")

            if self.NOT_FOUND_TEXT.lower() in body_lower:
                reasons.append("not_found_phrase_detected")

            title_match = re.search(r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip().lower()
                if "server error" in title or "internal server error" in title:
                    reasons.append("server_error_title_detected")

        except requests.RequestException as exc:
            reasons.append(f"http_request_error_{exc.__class__.__name__}")

        if not reasons:
            return None

        return MenuLinkFailure(
            level=link.level,
            label=link.label,
            requested_url=link.url,
            final_url=final_url,
            status_code=status_code,
            reasons=tuple(reasons),
        )

    def _workers(self) -> int:
        raw = os.getenv("MENU_LINKS_WORKERS", "").strip()
        if not raw:
            return self.DEFAULT_WORKERS
        try:
            value = int(raw)
        except ValueError:
            return self.DEFAULT_WORKERS
        return max(1, min(value, 32))

    def _redirected_to_home(self, requested_url: str, final_url: str) -> bool:
        requested_path = urlsplit(requested_url).path.rstrip("/")
        final_path = urlsplit(final_url).path.rstrip("/")

        home_paths = {"/en_GB"}
        if requested_path in home_paths:
            return False
        return final_path in home_paths
