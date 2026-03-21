from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from pages.social_links_page import SocialLink, SocialLinksPage


@dataclass(frozen=True)
class SocialLinkFailure:
    platform: str
    label: str
    requested_url: str
    final_url: str | None
    reason: str


class SocialLinksFlow:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.social_page = SocialLinksPage(page)

    def open_home_and_collect_links(self) -> list[SocialLink]:
        self.social_page.open_home(self.base_url)
        links = self.social_page.collect_visible_social_links()
        links.sort(key=lambda item: (item.platform, item.display_name, item.href))
        return links

    def validate_links(self, links: list[SocialLink]) -> list[SocialLinkFailure]:
        failures: list[SocialLinkFailure] = []

        for idx, link in enumerate(links, start=1):
            print(f"[SOCIAL][CHECK] {idx}/{len(links)} {link.display_name} -> {link.href}")
            final_url: str | None = None
            try:
                final_url = self.social_page.open_social_link_and_get_final_url(link)
                if not self._matches_expected_domain(link.platform, final_url):
                    failures.append(
                        SocialLinkFailure(
                            platform=link.platform,
                            label=link.display_name,
                            requested_url=link.href,
                            final_url=final_url,
                            reason="wrong_platform_domain",
                        )
                    )
            except Exception as exc:
                failures.append(
                    SocialLinkFailure(
                        platform=link.platform,
                        label=link.display_name,
                        requested_url=link.href,
                        final_url=final_url,
                        reason=f"navigation_error_{type(exc).__name__}",
                    )
                )

        return failures

    @staticmethod
    def _matches_expected_domain(platform: str, url: str) -> bool:
        platform_domains = SocialLinksPage.PLATFORM_DOMAINS.get(platform, ())
        lower_url = url.lower()
        return any(domain in lower_url for domain in platform_domains)
