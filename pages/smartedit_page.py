from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page, expect


@dataclass(frozen=True)
class AddedComponent:
    component_id: str
    component_name: str
    slot_id: str


class SmartEditPage:
    COMPONENT_EDITOR_TITLE_RE: Pattern[str] = re.compile(r"Amplience\s+CMS\s+Component\s+Editor", re.I)
    ADDED_ALERT_RE: Pattern[str] = re.compile(
        r"component\s+([A-Za-z0-9_]+)\s+has\s+been\s+successfully\s+added\s+to\s+slot\s+([A-Za-z0-9_-]+)",
        re.I,
    )

    def __init__(self, page: Page):
        self.page = page

    def open_login(self, smartedit_url: str, timeout: int = 60000):
        for attempt in range(3):
            try:
                self.page.goto(smartedit_url, wait_until="domcontentloaded", timeout=timeout)
                break
            except PlaywrightError:
                if attempt == 2:
                    raise
                self.page.wait_for_timeout(1200)
        retries = max(int(timeout / 500), 1)
        for _ in range(retries):
            username = self._login_username_input()
            password = self._login_password_input()
            if username.is_visible() and password.is_visible():
                return
            if self._smartedit_shell_visible():
                return
            self.page.wait_for_timeout(500)

        username = self._login_username_input()
        password = self._login_password_input()
        expect(username).to_be_visible(timeout=timeout)
        expect(password).to_be_visible(timeout=timeout)

    def login(self, username: str, password: str, timeout: int = 60000):
        username_input = self._login_username_input()
        password_input = self._login_password_input()
        if username_input.is_visible() and password_input.is_visible():
            username_input.fill(username)
            password_input.fill(password)
            sign_in_button = self.page.locator("button[name='submit'], button:has-text('Sign In')").first
            expect(sign_in_button).to_be_visible(timeout=timeout)
            sign_in_button.click()
        expect(self.page.get_by_text("SmartEdit")).to_be_visible(timeout=timeout)

    def select_site(self, site_label: str, timeout: int = 60000):
        site_trigger = self.page.locator("button.fd-select-button-custom.toggle-button").first
        expect(site_trigger).to_be_visible(timeout=timeout)

        current_site = site_trigger.inner_text().strip()
        if re.search(re.escape(site_label), current_site, re.I):
            return

        site_trigger.click()

        search_input = self.page.locator(
            "input[placeholder*='Select an Option'], input[aria-label*='Select an Option']"
        ).first
        if search_input.is_visible():
            search_input.fill(site_label)
            self.page.wait_for_timeout(350)

        target_site = self.page.locator(
            ".menu-option .se-item-printer-text, .menu-option, [role='option'], li"
        ).filter(has_text=re.compile(rf"^{re.escape(site_label)}$", re.I)).first

        if not target_site.is_visible():
            target_site = self.page.locator(
                ".menu-option .se-item-printer-text, .menu-option, [role='option'], li"
            ).filter(has_text=re.compile(re.escape(site_label), re.I)).first

        expect(target_site).to_be_visible(timeout=timeout)
        target_site.click()

        expect(self.page.get_by_text(site_label)).to_be_visible(timeout=timeout)

    def open_staged_pages(self, catalog_name: str, timeout: int = 60000):
        if "/#/pages/" in self.page.url and "/Staged" in self.page.url:
            return

        catalog_card = self.page.locator("se-catalog-details").filter(
            has_text=re.compile(re.escape(catalog_name), re.I)
        ).first
        expect(catalog_card).to_be_visible(timeout=timeout)

        staged_pages_link = catalog_card.locator("a[href*='/Staged']").filter(
            has_text=re.compile(r"Pages", re.I)
        ).first
        expect(staged_pages_link).to_be_visible(timeout=timeout)
        staged_pages_link.click()

        self.page.wait_for_url(re.compile(r".*/smartedit/#/pages/.*/Staged"), timeout=timeout)
        expect(self.page.get_by_role("heading", name=re.compile(r"Pages", re.I))).to_be_visible(timeout=timeout)
        # Requested stabilization: after opening Pages, wait and close cookie banner explicitly.
        self.page.wait_for_timeout(5000)
        self.accept_cookie_after_pages_open(timeout=20000)

    def open_page_builder(self, search_query: str, page_name: str, timeout: int = 60000):
        search = self.page.get_by_role("searchbox", name=re.compile(r"Pages", re.I)).first
        expect(search).to_be_visible(timeout=timeout)
        search.fill(search_query)
        self.page.wait_for_timeout(400)

        target_page = self.page.get_by_role("link", name=re.compile(rf"^{re.escape(page_name)}$", re.I)).first
        expect(target_page).to_be_visible(timeout=timeout)
        target_page.click()

        self.page.wait_for_url(re.compile(r".*/smartedit/#/storefront"), timeout=timeout)
        expect(self.page.locator("button.se-perspective-selector__btn").first).to_be_visible(timeout=timeout)
        self.wait_for_storefront_frame(timeout=timeout)
        # User-requested sequence: after opening the page builder storefront, wait and accept cookies.
        self.page.wait_for_timeout(5000)
        self.accept_cookie_after_pages_open(timeout=20000)
        # Fast no-op when banner is absent; prevents long waits after cookies are already accepted.
        self.accept_storefront_cookie_if_present(timeout=6000)

    def ensure_edit_toolbar(self, timeout: int = 60000):
        component_button = self.page.get_by_role("button", name=re.compile(r"^\s*Component\s*$", re.I)).first
        perspective_button = self.page.locator("button.se-perspective-selector__btn").first
        expect(perspective_button).to_be_visible(timeout=timeout)

        perspective_text = perspective_button.inner_text().strip().lower()
        if component_button.is_visible() and "preview" not in perspective_text:
            return

        # Cookie banner can block interaction with the perspective selector.
        self.accept_storefront_cookie_if_present(timeout=12000)

        perspective_button.click()

        advanced_edit = self.page.get_by_role("menuitem", name=re.compile(r"Advanced\s*Edit", re.I)).first
        basic_edit = self.page.get_by_role("menuitem", name=re.compile(r"Basic\s*Edit", re.I)).first

        if advanced_edit.is_visible():
            advanced_edit.click()
        elif basic_edit.is_visible():
            # Fallback only when Advanced is unavailable in this SmartEdit setup.
            basic_edit.click()
        else:
            raise AssertionError("SmartEdit perspective menu does not contain Basic/Advanced Edit option")

        expect(component_button).to_be_visible(timeout=timeout)
        self.wait_for_storefront_frame(timeout=timeout)

    def add_amplience_component_to_slot(
        self,
        component_name: str,
        amplience_slot_id: str,
        target_slot_id: str,
        component_type_label: str = "Amplience CMS Component",
        timeout: int = 60000,
    ) -> AddedComponent:
        self.accept_storefront_cookie_if_present(timeout=12000)

        component_card = self._prepare_component_card(
            component_type_label=component_type_label,
            timeout=timeout,
        )

        frame = self.wait_for_storefront_frame(timeout=timeout)
        slot_overlay, resolved_slot_id = self._resolve_target_slot(frame=frame, preferred_slot_id=target_slot_id)
        expect(slot_overlay).to_be_visible(timeout=timeout)

        if not component_card.is_visible():
            component_card = self._prepare_component_card(
                component_type_label=component_type_label,
                timeout=timeout,
            )

        self._drag(component_card, slot_overlay, timeout=timeout)

        editor_title = self.page.get_by_role("heading", name=self.COMPONENT_EDITOR_TITLE_RE).first
        expect(editor_title).to_be_visible(timeout=timeout)

        name_input = self.page.locator(
            "#name-shortstring, input[id*='name-shortstring'], input[name='name']"
        ).first
        slot_id_input = self.page.locator(
            "#amplienceSlotId-shortstring, input[id*='amplienceSlotId-shortstring']"
        ).first
        expect(name_input).to_be_visible(timeout=timeout)
        expect(slot_id_input).to_be_visible(timeout=timeout)

        name_input.fill(component_name)
        slot_id_input.fill(amplience_slot_id)

        save_button = self.page.get_by_role("button", name=re.compile(r"^Save$", re.I)).first
        expect(save_button).to_be_enabled(timeout=timeout)
        save_button.click()

        alert = self.page.locator("[role='alert']").filter(
            has_text=re.compile(r"successfully\s+added\s+to\s+slot", re.I)
        ).first
        expect(alert).to_be_visible(timeout=timeout)
        message = alert.inner_text()

        added_match = self.ADDED_ALERT_RE.search(message)
        if not added_match:
            raise AssertionError(f"Could not parse SmartEdit add-component message: {message}")

        return AddedComponent(
            component_id=added_match.group(1),
            component_name=component_name,
            slot_id=added_match.group(2) or resolved_slot_id,
        )

    def set_ready_to_sync(self, timeout: int = 60000, force: bool = False):
        status_button = self._status_button(timeout=timeout)
        try:
            current_status = status_button.inner_text().lower()
        except PlaywrightError:
            self.ensure_edit_toolbar(timeout=min(timeout, 20000))
            status_button = self._status_button(timeout=timeout)
            try:
                current_status = status_button.inner_text().lower()
            except PlaywrightError:
                return

        if "ready to sync" in current_status and not force:
            return

        status_button.click()
        ready_option = self.page.get_by_role("menuitem", name=re.compile(r"Ready\s*To\s*Sync", re.I)).first
        if not ready_option.is_visible():
            if "ready to sync" in current_status:
                self.page.keyboard.press("Escape")
                return
            self.page.keyboard.press("Escape")
            raise AssertionError("Ready To Sync option is not available in page status menu")
        ready_option.click()

        updated_status_button = self._status_button(timeout=timeout)
        try:
            updated_status_text = updated_status_button.inner_text().lower()
        except PlaywrightError:
            return
        if (
            "ready to sync" in updated_status_text
            or "synched" in updated_status_text
            or "draft not published yet" in updated_status_text
        ):
            return

        self.page.wait_for_timeout(1200)
        try:
            updated_status_text = updated_status_button.inner_text().lower()
        except PlaywrightError:
            return
        if (
            "ready to sync" not in updated_status_text
            and "synched" not in updated_status_text
            and "draft not published yet" not in updated_status_text
        ):
            raise AssertionError(
                f"Unexpected SmartEdit page status after selecting Ready To Sync: {updated_status_text}"
            )

    def sync_all_slots_and_page_information(self, timeout: int = 120000):
        sync_toolbar_button = self._sync_toolbar_button(timeout=timeout)
        sync_toolbar_button.click()

        all_slots_checkbox = self.page.get_by_role(
            "checkbox", name=re.compile(r"All Slots and Page Information", re.I)
        ).first
        expect(all_slots_checkbox).to_be_visible(timeout=timeout)
        if all_slots_checkbox.is_disabled():
            warning = self.page.get_by_text(
                re.compile(r"To sync, update page status to Ready to Sync", re.I)
            ).first
            if warning.is_visible():
                raise AssertionError("Page is not Ready To Sync. Unable to run synchronization.")
            raise AssertionError("Sync dialog is visible, but All Slots checkbox is disabled.")

        if not all_slots_checkbox.is_checked():
            all_slots_checkbox.click()

        sync_confirm_button = self.page.get_by_role("button", name=re.compile(r"^Sync$", re.I)).last
        expect(sync_confirm_button).to_be_enabled(timeout=timeout)
        sync_confirm_button.click()
        # Wait until sync dialog closes (or at least starts processing), without hard-blocking only on "Synched" text.
        retries = max(int(min(timeout, 45000) / 1000), 1)
        for _ in range(retries):
            warning = self.page.get_by_text(
                re.compile(r"To sync, update page status to Ready to Sync", re.I)
            ).first
            if warning.count() > 0 and warning.is_visible():
                raise AssertionError("Page is not Ready To Sync. Unable to run synchronization.")

            try:
                if not all_slots_checkbox.is_visible():
                    break
            except PlaywrightError:
                break
            self.page.wait_for_timeout(1000)

        # Stabilization pause before moving to storefront verification.
        self.page.wait_for_timeout(2500)

    def assert_component_rendered_on_storefront(
        self,
        storefront_url: str,
        component_heading: str,
        timeout: int = 60000,
    ):
        preview_page = self.page.context.new_page()
        try:
            preview_page.bring_to_front()
            heading = preview_page.get_by_role("heading", name=re.compile(re.escape(component_heading), re.I)).first

            # Synchronization can be eventually-consistent: retry page reloads until heading appears.
            retries = max(int(timeout / 5000), 1)
            heading_visible = False
            for _ in range(retries):
                preview_page.goto(storefront_url, wait_until="domcontentloaded", timeout=timeout)
                preview_page.wait_for_timeout(1800)
                if heading.is_visible():
                    heading_visible = True
                    break
                preview_page.wait_for_timeout(2500)

            if not heading_visible:
                raise AssertionError(
                    f"Component heading '{component_heading}' was not visible on storefront page: {storefront_url}"
                )

            preview_page.wait_for_timeout(1200)

            preview_page.mouse.wheel(0, 2500)
            preview_page.wait_for_timeout(700)
            footer = preview_page.locator("footer, [role='contentinfo']").first
            if footer.count() > 0:
                expect(footer).to_be_visible(timeout=timeout)

            preview_page.mouse.wheel(0, -2500)
            preview_page.wait_for_timeout(700)
            expect(heading).to_be_visible(timeout=timeout)
            preview_page.wait_for_timeout(1200)
        finally:
            self.page.bring_to_front()
            preview_page.close()

    def remove_amplience_component(self, component_id: str, timeout: int = 60000):
        frame = self.wait_for_storefront_frame(timeout=timeout)
        component = frame.locator(
            f"smartedit-element[data-smartedit-component-id='{component_id}']"
        ).first
        expect(component).to_be_visible(timeout=timeout)

        component.scroll_into_view_if_needed()
        box = component.bounding_box()
        if not box:
            raise AssertionError(f"Unable to get bounding box for component '{component_id}'")
        self.page.mouse.move(box["x"] + (box["width"] / 2), box["y"] + 20)
        self.page.wait_for_timeout(350)
        component.click(force=True)
        self.page.wait_for_timeout(250)

        remove_button = frame.locator(f"[id^='Remove-{component_id}-AmplienceCMSComponent-']").first
        if not self._is_locator_visible(remove_button):
            fallback_candidates = [
                frame.locator(f"[id*='Remove-{component_id}']").first,
                frame.get_by_role("button", name=re.compile(r"Remove", re.I)).first,
                frame.locator("[id*='Remove-']:visible").first,
                frame.locator("[aria-label*='Remove'], [title*='Remove']").first,
                self.page.get_by_role("button", name=re.compile(r"Remove", re.I)).first,
                self.page.get_by_role("button", name=re.compile(r"Delete", re.I)).first,
            ]
            for candidate in fallback_candidates:
                if self._is_locator_visible(candidate):
                    remove_button = candidate
                    break

        expect(remove_button).to_be_visible(timeout=timeout)
        remove_button.click(force=True)

        remove_dialog = self.page.get_by_text(re.compile(r"Remove Component", re.I)).first
        expect(remove_dialog).to_be_visible(timeout=timeout)

        ok_button = self.page.get_by_role("button", name=re.compile(r"^OK$|^Ok$|Remove|Confirm", re.I)).first
        expect(ok_button).to_be_visible(timeout=timeout)
        ok_button.click()

        self._wait_for_component_removal(frame=frame, component_id=component_id, timeout=timeout)

    def wait_for_storefront_frame(self, timeout: int = 60000) -> Frame:
        retries = max(int(timeout / 500), 1)

        for _ in range(retries):
            named_frame = self.page.frame(name="ySmartEditFrame")
            if self._is_initialized_frame(named_frame):
                return named_frame

            frame_candidates = []
            for frame in self.page.frames:
                if frame == self.page.main_frame:
                    continue
                if not self._is_initialized_frame(frame):
                    continue
                frame_candidates.append(frame)

            if frame_candidates:
                preview_frame = next(
                    (frame for frame in frame_candidates if "preview-content" in (frame.url or "")),
                    None,
                )
                return preview_frame or frame_candidates[0]

            # Fallback for SmartEdit layouts that render storefront directly in main frame.
            if "/#/storefront" in self.page.url:
                try:
                    has_slot_markup = self.page.evaluate(
                        """
                        () => Boolean(
                          document.querySelector(
                            "[data-smartedit-component-id], [id$='_ContentSlot_overlay'], [data-smartedit-component-type='ContentSlot']"
                          )
                        )
                        """
                    )
                    if has_slot_markup:
                        return self.page.main_frame
                except PlaywrightError:
                    pass
            self.page.wait_for_timeout(500)

        if "/#/storefront" in self.page.url:
            return self.page.main_frame

        raise AssertionError("SmartEdit storefront frame was not initialized")

    def accept_storefront_cookie_if_present(self, timeout: int = 20000):
        frame = self.wait_for_storefront_frame(timeout=timeout)
        retries = max(int(min(timeout, 6000) / 500), 1)
        cookie_selector = (
            "#onetrust-accept-btn-handler, "
            "button:has-text('Accept All Cookies'), "
            "button:has-text('Accept All')"
        )

        for _ in range(retries):
            saw_cookie_control = False
            for root in (frame, self.page):
                try:
                    accept_cookie = root.locator(cookie_selector).first
                    count = accept_cookie.count()
                    if count > 0:
                        saw_cookie_control = True
                    if count > 0 and accept_cookie.is_visible():
                        accept_cookie.click(force=True)
                        self.page.wait_for_timeout(300)
                        return

                    clicked_by_js = root.evaluate(
                        """
                        () => {
                          const direct = document.querySelector('#onetrust-accept-btn-handler');
                          if (direct) {
                            direct.click();
                            return true;
                          }
                          const byText = Array.from(document.querySelectorAll('button')).find((btn) =>
                            (btn.textContent || '').toLowerCase().includes('accept all cookies')
                          );
                          if (byText) {
                            byText.click();
                            return true;
                          }
                          return false;
                        }
                        """
                    )
                    if clicked_by_js:
                        self.page.wait_for_timeout(300)
                        return
                except PlaywrightError:
                    continue
            if not saw_cookie_control:
                return
            try:
                self.page.wait_for_timeout(500)
            except PlaywrightError:
                return

    def accept_cookie_after_pages_open(self, timeout: int = 20000):
        retries = max(int(min(timeout, 6000) / 500), 1)
        cookie_selector = (
            "#onetrust-accept-btn-handler, "
            "button:has-text('Accept All Cookies'), "
            "button:has-text('Accept All')"
        )

        for _ in range(retries):
            saw_cookie_control = False
            # Main document first
            main_accept = self.page.locator(cookie_selector).first
            try:
                main_count = main_accept.count()
                if main_count > 0:
                    saw_cookie_control = True
                if main_count > 0 and main_accept.is_visible():
                    main_accept.click(force=True)
                    self.page.wait_for_timeout(300)
                    return
            except PlaywrightError:
                pass

            # Then all frames (SmartEdit can render storefront/cookie inside nested frames)
            for frame in self.page.frames:
                try:
                    frame_accept = frame.locator(cookie_selector).first
                    frame_count = frame_accept.count()
                    if frame_count > 0:
                        saw_cookie_control = True
                    if frame_count > 0 and frame_accept.is_visible():
                        frame_accept.click(force=True)
                        self.page.wait_for_timeout(300)
                        return
                except PlaywrightError:
                    continue

            # JS fallback in main page
            try:
                clicked_by_js = self.page.evaluate(
                    """
                    () => {
                      const direct = document.querySelector('#onetrust-accept-btn-handler');
                      if (direct) {
                        direct.click();
                        return true;
                      }
                      const byText = Array.from(document.querySelectorAll('button')).find((btn) => {
                        const txt = (btn.textContent || '').toLowerCase();
                        return txt.includes('accept all cookies') || txt.includes('accept all');
                      });
                      if (byText) {
                        byText.click();
                        return true;
                      }
                      return false;
                    }
                    """
                )
                if clicked_by_js:
                    self.page.wait_for_timeout(300)
                    return
            except PlaywrightError:
                pass

            if not saw_cookie_control:
                return

            self.page.wait_for_timeout(500)

    def _open_component_types_panel(self, timeout: int = 60000):
        component_button = self.page.get_by_role("button", name=re.compile(r"^\s*Component\s*$", re.I)).first
        expect(component_button).to_be_visible(timeout=timeout)
        panel_marker = self.page.locator(
            "input[placeholder*='Search component type by name'], "
            "input[aria-label*='Search component type by name'], "
            ".se-component-item"
        ).first

        if panel_marker.count() > 0 and panel_marker.is_visible():
            return

        component_button.click()
        expect(panel_marker).to_be_visible(timeout=timeout)

    def _drag(self, source, target, timeout: int = 60000):
        for _ in range(6):
            try:
                source.drag_to(target, force=True, timeout=5000)
                editor_visible = self.page.get_by_role("heading", name=self.COMPONENT_EDITOR_TITLE_RE).first
                if editor_visible.is_visible():
                    return
            except PlaywrightError:
                pass

            try:
                target.scroll_into_view_if_needed(timeout=2000)
            except PlaywrightError:
                pass

            try:
                source_box = source.bounding_box()
                target_box = target.bounding_box()
            except PlaywrightError:
                self.page.wait_for_timeout(300)
                continue
            if not source_box or not target_box:
                self.page.wait_for_timeout(300)
                continue

            source_x = source_box["x"] + source_box["width"] / 2
            source_y = source_box["y"] + source_box["height"] / 2
            drop_points = [
                (target_box["x"] + 40, target_box["y"] + target_box["height"] / 2),
                (target_box["x"] + target_box["width"] / 2, target_box["y"] + target_box["height"] / 2),
                (target_box["x"] + min(target_box["width"] - 40, 220), target_box["y"] + target_box["height"] / 2),
            ]

            for drop_x, drop_y in drop_points:
                self.page.mouse.move(source_x, source_y)
                self.page.wait_for_timeout(250)
                self.page.mouse.down()
                self.page.wait_for_timeout(300)
                self.page.mouse.move(drop_x, max(drop_y - 4, target_box["y"] + 2), steps=80)
                self.page.wait_for_timeout(350)
                self.page.mouse.move(drop_x, drop_y + 2, steps=20)
                self.page.wait_for_timeout(250)
                self.page.mouse.up()
                self.page.wait_for_timeout(1200)

                editor_visible = self.page.get_by_role("heading", name=self.COMPONENT_EDITOR_TITLE_RE).first
                if editor_visible.is_visible():
                    return

            self.page.wait_for_timeout(700)

        raise AssertionError("Failed to drag Amplience component into target SmartEdit slot")

    def _prepare_component_card(self, component_type_label: str, timeout: int = 60000):
        self._open_component_types_panel(timeout=timeout)
        search_box = self.page.locator(
            "input[placeholder*='Search component type by name'], "
            "input[aria-label*='Search component type by name'], "
            "input.se-input-group__input-area"
        ).first
        if not search_box.is_visible():
            search_box = self.page.get_by_role("searchbox").first
        expect(search_box).to_be_visible(timeout=timeout)
        # Type slowly to reduce SmartEdit flakiness in component filtering.
        search_box.click()
        search_box.press("ControlOrMeta+A")
        search_box.press("Backspace")
        search_box.type(component_type_label, delay=140)
        self.page.wait_for_timeout(900)

        component_card = self.page.locator(".se-component-item:visible").filter(
            has_text=re.compile(re.escape(component_type_label), re.I)
        ).first
        if component_card.count() == 0:
            component_card = self.page.locator(".se-component-item").filter(
                has_text=re.compile(re.escape(component_type_label), re.I)
            ).first
        expect(component_card).to_be_visible(timeout=timeout)
        self.page.wait_for_timeout(800)
        return component_card

    def _status_button(self, timeout: int = 60000):
        status_button = self.page.locator("button.se-display-draft__icon").first
        if not status_button.is_visible():
            self.ensure_edit_toolbar(timeout=min(timeout, 20000))
        expect(status_button).to_be_visible(timeout=timeout)
        return status_button

    def _sync_toolbar_button(self, timeout: int = 60000):
        sync_toolbar_button = self.page.locator("button[title='Synchronization']").first
        expect(sync_toolbar_button).to_be_visible(timeout=timeout)
        return sync_toolbar_button

    def _wait_for_component_removal(self, frame: Frame, component_id: str, timeout: int = 60000):
        retries = max(int(timeout / 500), 1)
        for _ in range(retries):
            remaining = frame.eval_on_selector_all(
                f"smartedit-element[data-smartedit-component-id='{component_id}']",
                "els => els.length",
            )
            if remaining == 0:
                return
            self.page.wait_for_timeout(500)

        raise AssertionError(f"Component '{component_id}' was not removed from SmartEdit page")

    def _resolve_target_slot(self, frame: Frame, preferred_slot_id: str) -> tuple:
        if preferred_slot_id:
            preferred_overlay = frame.locator(f"#{preferred_slot_id}_ContentSlot_overlay").first
            if preferred_overlay.count() > 0:
                return preferred_overlay, preferred_slot_id

            preferred_slot = frame.locator(f"[data-smartedit-component-id='{preferred_slot_id}']").first
            if preferred_slot.count() > 0:
                return preferred_slot, preferred_slot_id

        fallback_slot_id = frame.evaluate(
            """
            () => {
              const slots = [];
              const seen = new Set();

              const byAttr = Array.from(
                document.querySelectorAll("[data-smartedit-component-type='ContentSlot'][data-smartedit-component-id]")
              );
              for (const el of byAttr) {
                const id = el.getAttribute("data-smartedit-component-id") || "";
                if (!id || seen.has(id) || !/^Content\\d+Slot-/.test(id)) continue;
                seen.add(id);
                const match = id.match(/^Content(\\d+)Slot-/);
                slots.push({
                  id,
                  index: match ? Number(match[1]) : 0,
                  textLen: (el.textContent || "").replace(/\\s+/g, " ").trim().length,
                });
              }

              const byOverlay = Array.from(document.querySelectorAll("[id$='_ContentSlot_overlay']"));
              for (const el of byOverlay) {
                const raw = el.getAttribute("id") || "";
                const id = raw.replace(/_ContentSlot_overlay$/, "");
                if (!id || seen.has(id) || !/^Content\\d+Slot-/.test(id)) continue;
                seen.add(id);
                const match = id.match(/^Content(\\d+)Slot-/);
                slots.push({
                  id,
                  index: match ? Number(match[1]) : 0,
                  textLen: 0,
                });
              }

              slots.sort((a, b) => a.index - b.index);

              const emptyBelow = slots.find((s) => s.index >= 3 && s.textLen < 20);
              if (emptyBelow) return emptyBelow.id;

              const anyEmpty = slots.find((s) => s.textLen < 20);
              if (anyEmpty) return anyEmpty.id;

              return slots.length ? slots[0].id : null;
            }
            """
        )

        if not fallback_slot_id:
            raise AssertionError("Could not resolve a target Content*Slot in SmartEdit storefront")

        overlay = frame.locator(f"#{fallback_slot_id}_ContentSlot_overlay").first
        if overlay.count() > 0:
            return overlay, fallback_slot_id

        slot = frame.locator(f"[data-smartedit-component-id='{fallback_slot_id}']").first
        return slot, fallback_slot_id

    def _login_username_input(self):
        return self.page.locator(
            "input[name='username'], input[placeholder*='User Name'], input[placeholder*='User name']"
        ).first

    def _login_password_input(self):
        return self.page.locator(
            "input[name='password'], input[placeholder*='Password'], input[type='password']"
        ).first

    def _smartedit_shell_visible(self) -> bool:
        site_selector = self.page.locator("button.fd-select-button-custom.toggle-button").first
        toolbar = self.page.locator("div.se-toolbar").first
        smartedit_title = self.page.get_by_text("SmartEdit").first
        return site_selector.is_visible() or toolbar.is_visible() or smartedit_title.is_visible()

    @staticmethod
    def _is_locator_visible(locator) -> bool:
        try:
            return locator.count() > 0 and locator.is_visible()
        except PlaywrightError:
            return False

    @staticmethod
    def _is_initialized_frame(frame: Frame | None) -> bool:
        if not frame:
            return False
        url = (frame.url or "").strip()
        return bool(url and url != "about:blank")
