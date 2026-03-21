from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect

from utils.consent import dismiss_onetrust


@dataclass(frozen=True)
class SocialLink:
    platform: str
    display_name: str
    href: str


class SocialLinksPage:
    PLATFORM_DOMAINS = {
        "facebook": ("facebook.com",),
        "youtube": ("youtube.com",),
        "twitter": ("twitter.com", "x.com"),
        "instagram": ("instagram.com",),
        "linkedin": ("linkedin.com",),
        "pinterest": ("pinterest.com",),
        "tiktok": ("tiktok.com",),
    }

    def __init__(self, page: Page):
        self.page = page

    def open_home(self, base_url: str, timeout: int = 60000):
        self.page.goto(base_url, wait_until="domcontentloaded", timeout=timeout)
        dismiss_onetrust(self.page)

    def collect_visible_social_links(self) -> list[SocialLink]:
        rows = self.page.evaluate(
            """
            (platformDomains) => {
              const links = Array.from(document.querySelectorAll("a[href]"));
              const collected = [];
              const seen = new Set();

              for (const link of links) {
                const href = (link.href || "").trim();
                if (!href) continue;

                const rect = link.getBoundingClientRect();
                const visible = !!(rect.width || rect.height);
                if (!visible) continue;

                const lowerHref = href.toLowerCase();
                let matchedPlatform = null;
                for (const [platform, domains] of Object.entries(platformDomains)) {
                  if (domains.some((domain) => lowerHref.includes(domain))) {
                    matchedPlatform = platform;
                    break;
                  }
                }
                if (!matchedPlatform) continue;

                if (seen.has(href)) continue;
                seen.add(href);

                const label =
                  (link.getAttribute("aria-label") || "").trim() ||
                  (link.getAttribute("title") || "").trim() ||
                  (link.textContent || "").trim() ||
                  matchedPlatform;

                collected.push({
                  platform: matchedPlatform,
                  display_name: label,
                  href: href,
                });
              }

              return collected;
            }
            """,
            self.PLATFORM_DOMAINS,
        )

        return [
            SocialLink(
                platform=str(row["platform"]).strip().lower(),
                display_name=str(row["display_name"]).strip(),
                href=str(row["href"]).strip(),
            )
            for row in rows
        ]

    def open_social_link_and_get_final_url(self, link: SocialLink, timeout: int = 30000) -> str:
        link_locator = self._resolve_link_locator(link)
        expect(link_locator).to_be_visible(timeout=timeout)
        link_locator.scroll_into_view_if_needed(timeout=timeout)

        before_url = self.page.url
        popup_page = None

        try:
            with self.page.context.expect_page(timeout=timeout) as popup_info:
                link_locator.click()
            popup_page = popup_info.value
            popup_page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return popup_page.url
        except PlaywrightError:
            # Fallback for links that navigate in the same tab.
            link_locator.click()
            self.page.wait_for_timeout(1500)
            if self.page.url == before_url:
                raise AssertionError(
                    f"Social link '{link.display_name}' did not open new page and did not navigate current tab."
                )
            final_url = self.page.url
            self.page.go_back(wait_until="domcontentloaded", timeout=timeout)
            return final_url
        finally:
            if popup_page and not popup_page.is_closed():
                popup_page.close()
            if self.page.is_closed():
                raise AssertionError(f"Main page was unexpectedly closed while validating '{link.display_name}'")

    def _resolve_link_locator(self, link: SocialLink):
        if link.display_name:
            by_name = self.page.get_by_role("link", name=re.compile(re.escape(link.display_name), re.I)).first
            if by_name.count() > 0:
                return by_name

        by_exact_href = self.page.locator(f"a[href='{link.href}']").first
        if by_exact_href.count() > 0:
            return by_exact_href

        href_without_query = link.href.split("?")[0]
        return self.page.locator(f"a[href^='{href_without_query}']").first
