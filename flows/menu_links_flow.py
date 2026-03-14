from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

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

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.home_url = f"{self.base_url}/en_GB"
        self.menu = MenuNavigationPage(page)

    def open_home_and_collect_links(self) -> list[MenuLink]:
        self.page.goto(self.home_url, wait_until="domcontentloaded", timeout=45000)
        dismiss_onetrust(self.page)
        return self.menu.collect_internal_links()

    def validate_links(self, links: list[MenuLink], timeout: int = 45000) -> list[MenuLinkFailure]:
        failures: list[MenuLinkFailure] = []

        for index, link in enumerate(links, start=1):
            print(f"[MENU][CHECK] {index}/{len(links)} [{link.level}] {link.label} -> {link.url}")

            reasons: list[str] = []
            status_code: int | None = None
            final_url = ""

            try:
                response, final_url, timed_out_without_navigation = self._open_link(link.url, timeout=timeout)
                status_code = response.status if response else None

                if status_code is not None and status_code >= 400:
                    reasons.append(f"http_status_{status_code}")

                if self._redirected_to_home(link.url, final_url):
                    reasons.append("redirected_to_homepage")

                if timed_out_without_navigation:
                    reasons.append("navigation_timeout_no_navigation")

                page_text = self.page.evaluate("() => (document.body?.innerText || '').toLowerCase()")
                if self.NOT_FOUND_TEXT.lower() in (page_text or ""):
                    reasons.append("not_found_phrase_detected")

                title = (self.page.title() or "").lower()
                if "server error" in title or "internal server error" in title:
                    reasons.append("server_error_title_detected")

            except Exception as exc:
                reasons.append(f"navigation_error_{exc.__class__.__name__}")
                final_url = self.page.url

            if reasons:
                failures.append(
                    MenuLinkFailure(
                        level=link.level,
                        label=link.label,
                        requested_url=link.url,
                        final_url=final_url,
                        status_code=status_code,
                        reasons=tuple(reasons),
                    )
                )

        return failures

    def _open_link(self, url: str, timeout: int) -> tuple[object | None, str, bool]:
        response = None
        timed_out_without_navigation = False

        for attempt in range(2):
            start_url = self.page.url
            timed_out = False

            try:
                # commit is enough for link-health checks and avoids long waits on heavy pages
                response = self.page.goto(url, wait_until="commit", timeout=timeout)
            except PlaywrightTimeoutError:
                timed_out = True

            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=min(timeout, 20000))
            except PlaywrightTimeoutError:
                pass

            final_url = self.page.url
            if not timed_out or final_url != start_url:
                return response, final_url, False

            timed_out_without_navigation = True
            if attempt == 0:
                print(f"[MENU][RETRY] Timeout without navigation for {url}, retrying once")

        return response, self.page.url, timed_out_without_navigation

    def _redirected_to_home(self, requested_url: str, final_url: str) -> bool:
        requested_path = urlsplit(requested_url).path.rstrip("/")
        final_path = urlsplit(final_url).path.rstrip("/")

        home_paths = {"/en_GB"}
        if requested_path in home_paths:
            return False
        return final_path in home_paths
