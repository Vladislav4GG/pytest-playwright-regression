#!/usr/bin/env python3
"""Extract country/language combinations from site selector and build S1/S2 URLs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def build_url(site_code: str, locale: str, env: str) -> str:
    env = env.lower()
    host = f"{site_code}.cbnd-seikoepso3-{env}-public.model-t.cc.commerce.ondemand.com"
    return f"https://{host}/{locale}"


def extract_mapping(base_url: str) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(base_url, wait_until="domcontentloaded")

        accept_all = page.locator("#onetrust-accept-btn-handler").first
        if accept_all.is_visible():
            accept_all.click()

        page.locator(".js-site-selector-trigger").first.click()
        page.locator("form.js-site-selector-form").first.wait_for(state="visible")

        mapping = page.evaluate(
            """
            () => {
              const country = document.querySelector('#siteSelectorCountrydesktop');
              const language = document.querySelector('#siteSelectorLangdesktop');
              if (!country || !language) return [];

              const data = [];
              const countries = Array.from(country.options).map((o) => ({
                label: (o.textContent || '').trim(),
                value: o.value || '',
              }));

              for (const c of countries) {
                country.value = c.value;
                country.dispatchEvent(new Event('change', { bubbles: true }));

                const languages = Array.from(language.options).map((o) => ({
                  label: (o.textContent || '').trim(),
                  value: o.value || '',
                }));

                data.push({
                  country: c.label,
                  site_code: c.value,
                  languages,
                });
              }
              return data;
            }
            """
        )

        context.close()
        browser.close()
        return mapping


def build_payload(base_url: str, mapping: list[dict]) -> dict:
    countries: list[dict] = []
    for item in mapping:
        langs: list[dict] = []
        for lang in item["languages"]:
            locale = lang["value"]
            langs.append(
                {
                    "language": lang["label"],
                    "locale": locale,
                    "url_s1": build_url(item["site_code"], locale, "s1"),
                    "url_s2": build_url(item["site_code"], locale, "s2"),
                }
            )

        countries.append(
            {
                "country": item["country"],
                "site_code": item["site_code"],
                "default_locale": langs[0]["locale"] if langs else "",
                "default_url_s1": langs[0]["url_s1"] if langs else "",
                "default_url_s2": langs[0]["url_s2"] if langs else "",
                "languages": langs,
            }
        )

    focus = {}
    for name in ("Belgium", "Switzerland", "Europe"):
        for item in countries:
            if item["country"] == name:
                focus[name] = item["languages"]
                break

    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_base_url": base_url,
        "country_count": len(countries),
        "countries": countries,
        "focus_multi_locale_countries": focus,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB",
    )
    parser.add_argument(
        "--out",
        default="data/regression/site_selector_locales.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping = extract_mapping(args.base_url)
    payload = build_payload(args.base_url, mapping)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"Saved locale mapping to: {out}")
    print(f"Countries: {payload['country_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
