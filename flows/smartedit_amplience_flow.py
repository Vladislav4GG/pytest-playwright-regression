from __future__ import annotations

import random
from dataclasses import dataclass

from playwright.sync_api import Page

from pages.smartedit_page import SmartEditPage


@dataclass(frozen=True)
class SmartEditAmplienceConfig:
    smartedit_url: str
    smartedit_username: str
    smartedit_password: str

    site_label: str
    catalog_label: str

    page_search_query: str
    page_name: str
    storefront_page_url: str

    target_slot_id: str
    amplience_slot_id: str
    rendered_heading_text: str


@dataclass(frozen=True)
class SmartEditAmplienceResult:
    component_id: str
    component_name: str


class SmartEditAmplienceFlow:
    def __init__(self, page: Page, config: SmartEditAmplienceConfig):
        self.page = page
        self.config = config
        self.smartedit = SmartEditPage(page)

    def run(self) -> SmartEditAmplienceResult:
        cfg = self.config
        component_name = self._random_component_name()
        added_component_id = ""

        print("[SMARTEDIT][STEP] Open login page")
        self.smartedit.open_login(cfg.smartedit_url)
        print("[SMARTEDIT][STEP] Sign in to SmartEdit")
        self.smartedit.login(username=cfg.smartedit_username, password=cfg.smartedit_password)
        print(f"[SMARTEDIT][STEP] Select site: {cfg.site_label}")
        self.smartedit.select_site(site_label=cfg.site_label)
        print(f"[SMARTEDIT][STEP] Open staged pages in catalog: {cfg.catalog_label}")
        self.smartedit.open_staged_pages(catalog_name=cfg.catalog_label)
        print(f"[SMARTEDIT][STEP] Open page builder for: {cfg.page_name}")
        self.smartedit.open_page_builder(search_query=cfg.page_search_query, page_name=cfg.page_name)
        self.smartedit.ensure_edit_toolbar()

        try:
            print("[SMARTEDIT][STEP 1] Add Amplience component")
            added = self.smartedit.add_amplience_component_to_slot(
                component_name=component_name,
                amplience_slot_id=cfg.amplience_slot_id,
                target_slot_id=cfg.target_slot_id,
            )
            added_component_id = added.component_id

            self.page.wait_for_timeout(5000)
            self.smartedit.ensure_edit_toolbar()
            print("[SMARTEDIT][STEP 2] Draft -> Ready to Sync")
            self.smartedit.set_ready_to_sync(force=True)
            print("[SMARTEDIT][STEP 3] Sync -> Select All Slots and Page Information -> Sync")
            self.smartedit.sync_all_slots_and_page_information()

            print("[SMARTEDIT][STEP 4-5] Open storefront page and verify rendered text")
            self.smartedit.assert_component_rendered_on_storefront(
                storefront_url=cfg.storefront_page_url,
                component_heading=cfg.rendered_heading_text,
            )

            return SmartEditAmplienceResult(
                component_id=added.component_id,
                component_name=added.component_name,
            )
        finally:
            if added_component_id:
                print("[SMARTEDIT][STEP 6] Return to constructor and remove component")
                self.smartedit.ensure_edit_toolbar()
                self.smartedit.remove_amplience_component(component_id=added_component_id)
                self.smartedit.ensure_edit_toolbar()
                print("[SMARTEDIT][STEP 7] Draft -> Ready to Sync")
                self.smartedit.set_ready_to_sync(force=True)
                print("[SMARTEDIT][STEP 8] Sync -> Select All Slots and Page Information -> Sync")
                self.smartedit.sync_all_slots_and_page_information()

    @staticmethod
    def _random_component_name() -> str:
        return f"Ampience{random.randint(100000, 999999)}"
