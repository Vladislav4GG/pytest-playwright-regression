from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page


@dataclass(frozen=True)
class MenuLink:
    level: str
    label: str
    url: str


class MenuNavigationPage:
    MENU_ROOT_SELECTOR = "nav.navigation.navigation--bottom.js_navigation--bottom"

    def __init__(self, page: Page):
        self.page = page

    def collect_internal_links(self) -> list[MenuLink]:
        raw_links = self.page.evaluate(
            """
            ({ menuRootSelector }) => {
              const root = document.querySelector(menuRootSelector);
              if (!root) {
                return [];
              }

              const normalizeText = (value) => (value || "").replace(/\\s+/g, " ").trim();
              const isSkippableHref = (href) => {
                if (!href) return true;
                const lower = href.toLowerCase();
                if (href === "#" || lower.startsWith("javascript:")) return true;
                if (lower.startsWith("mailto:") || lower.startsWith("tel:")) return true;
                return false;
              };

              const levelFromLiClass = (liClass) => {
                if (liClass.includes("navigation-sub-sub__list-item")) return "sub_child";
                if (liClass.includes("navigation-sub__list-item")) return "child";
                if (liClass.includes("navigation__list-item")) return "parent";
                return null;
              };

              const links = [];
              const seen = new Set();

              for (const anchor of root.querySelectorAll("a[href]")) {
                const href = (anchor.getAttribute("href") || "").trim();
                if (isSkippableHref(href)) continue;

                const li = anchor.closest("li");
                const liClass = li?.className || "";
                const level = levelFromLiClass(liClass);
                if (!level) continue;

                if (liClass.includes("--back") || liClass.includes("hidden-md hidden-lg")) continue;

                const absoluteUrl = new URL(href, window.location.origin);
                if (absoluteUrl.origin !== window.location.origin) continue;

                absoluteUrl.hash = "";
                const url = absoluteUrl.toString();

                const key = url;
                if (seen.has(key)) continue;
                seen.add(key);

                links.push({
                  level,
                  label: normalizeText(anchor.textContent) || "<no-label>",
                  url,
                });
              }

              return links;
            }
            """,
            {"menuRootSelector": self.MENU_ROOT_SELECTOR},
        )

        return [MenuLink(level=item["level"], label=item["label"], url=item["url"]) for item in (raw_links or [])]
