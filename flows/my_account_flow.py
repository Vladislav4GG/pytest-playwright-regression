from __future__ import annotations

import random
import re
from dataclasses import dataclass

from playwright.sync_api import Page

from pages.my_account_page import AddressData, MyAccountPage, ProfileDetails


@dataclass(frozen=True)
class MyAccountConfig:
    base_url: str
    account_home_url: str
    email: str
    password: str
    loqate_postcode: str


@dataclass(frozen=True)
class MyAccountCaseResult:
    warnings: tuple[str, ...]
    notes: tuple[str, ...]


class MyAccountFlow:
    def __init__(self, page: Page, config: MyAccountConfig):
        self.page = page
        self.config = config
        self.account = MyAccountPage(page=page, base_url=config.base_url)

    def run_order_history_case(self) -> MyAccountCaseResult:
        warnings: list[str] = []
        notes: list[str] = []

        print("[MY_ACCOUNT][ORDER][STEP] Login and open account home")
        self._login(email=self.config.email, password=self.config.password)

        print("[MY_ACCOUNT][ORDER][STEP] Open Order History")
        self.account.open_order_history()

        selected = self.account.sort_order_history(value="byDate")
        assert selected == "byDate", f"Unexpected sort value after Date sort: {selected}"
        print("[MY_ACCOUNT][ORDER][PASS] Sorted by Date")

        selected = self.account.sort_order_history(value="byOrderNumber")
        assert selected == "byOrderNumber", f"Unexpected sort value after Order Number sort: {selected}"
        print("[MY_ACCOUNT][ORDER][PASS] Sorted by Order Number")

        order_code = self.account.open_first_order()
        details = self.account.read_order_details()
        assert order_code in details.order_number, (
            f"Opened order '{order_code}' but details page shows '{details.order_number}'"
        )
        assert details.status_text, "Order Status is not visible on order details page"
        assert details.date_placed_text, "Date Placed is not visible on order details page"
        assert details.shipping_text, "Shipping Method is not visible on order details page"
        assert details.payment_text, "Payment Method is not visible on order details page"
        assert details.email_text, "Email is not visible on order details page"
        print(f"[MY_ACCOUNT][ORDER][PASS] Order details are visible for {details.order_number}")

        reordered, reorder_url = self.account.click_reorder_if_available()
        if reordered:
            notes.append(f"reorder_url={reorder_url}")
            if not re.search(r"/cart|/checkout", reorder_url):
                warnings.append(f"Reorder was clicked but URL is not cart/checkout-like: {reorder_url}")
            print(f"[MY_ACCOUNT][ORDER][PASS] Reorder clicked, final URL: {reorder_url}")
            self._login(email=self.config.email, password=self.config.password)
            self.account.open_order_history()
            self.account.open_first_order()
        else:
            warnings.append("Reorder button is not available for sampled order (probably unavailable item).")
            print("[MY_ACCOUNT][ORDER][WARN] Reorder button is not available")

        back_url = self.account.click_back_to_your_account()
        assert "/my-account/home" in back_url, f"Back to Your Account did not open account home: {back_url}"
        print("[MY_ACCOUNT][ORDER][PASS] Back to Your Account works")

        return MyAccountCaseResult(warnings=tuple(warnings), notes=tuple(notes))

    def run_update_personal_details_case(self) -> MyAccountCaseResult:
        warnings: list[str] = []
        notes: list[str] = []

        print("[MY_ACCOUNT][PROFILE][STEP] Login and open Personal Details")
        self._login(email=self.config.email, password=self.config.password)
        self.account.open_update_personal_details()

        original = self.account.read_profile_details()
        updated = ProfileDetails(
            first_name=self._mutated_name(original.first_name, fallback="Vlad"),
            last_name=self._mutated_name(original.last_name, fallback="Ponomarenko"),
            telephone=original.telephone or "07123456789",
            day=original.day,
            month=original.month,
            year=original.year,
        )

        try:
            self.account.fill_profile_details(updated)
            self.account.submit_profile_update()
            self.account.open_update_personal_details()
            after_update = self.account.read_profile_details()
            assert after_update.first_name == updated.first_name, "First name was not saved"
            assert after_update.last_name == updated.last_name, "Last name was not saved"
            notes.append(f"updated_name={updated.first_name} {updated.last_name}")
            print("[MY_ACCOUNT][PROFILE][PASS] Valid personal details saved")

            self.account.clear_profile_required_fields()
            self.account.submit_profile_update()
            errors = self.account.collect_visible_form_errors()
            lowered = " ".join(errors).lower()
            assert "first name" in lowered, f"Validation for empty first name not shown. errors={errors}"
            assert "last name" in lowered, f"Validation for empty last name not shown. errors={errors}"
            print("[MY_ACCOUNT][PROFILE][PASS] Validation errors are shown for mandatory fields")
        finally:
            self.account.open_update_personal_details()
            self.account.fill_profile_details(original)
            self.account.submit_profile_update()
            print("[MY_ACCOUNT][PROFILE][INFO] Original personal details restored")

        return MyAccountCaseResult(warnings=tuple(warnings), notes=tuple(notes))

    def run_update_email_case(self) -> MyAccountCaseResult:
        warnings: list[str] = []
        notes: list[str] = []

        original_email = self.config.email
        password = self.config.password
        temp_email = self._random_email_alias(original_email, tag="updmail")
        active_email = original_email

        print("[MY_ACCOUNT][EMAIL][STEP] Login and open Update Email")
        try:
            self._login(email=original_email, password=password)
            self.account.open_update_email()

            self.account.submit_update_email_empty()
            errors = self.account.collect_visible_form_errors()
            lowered = " ".join(errors).lower()
            assert "required" in lowered, f"Expected required validation on empty email form. errors={errors}"
            print("[MY_ACCOUNT][EMAIL][PASS] Mandatory validation is shown")

            self.account.submit_update_email(new_email=temp_email, password=password)
            notes.append(f"temp_email={temp_email}")
            print(f"[MY_ACCOUNT][EMAIL][INFO] Requested email change to: {temp_email}")

            self.account.logout()
            if self._try_login(email=temp_email, password=password):
                active_email = temp_email
                print(f"[MY_ACCOUNT][EMAIL][PASS] Login with updated email works: {temp_email}")
            elif self._try_login(email=original_email, password=password):
                warnings.append("Email change did not apply; account still logs in with original email.")
                print("[MY_ACCOUNT][EMAIL][WARN] Email remained unchanged after submit")
            else:
                raise AssertionError("Unable to login with either original or updated email after email update submit")
        finally:
            if active_email != original_email:
                self._login(email=active_email, password=password)
                self.account.open_update_email()
                self.account.submit_update_email(new_email=original_email, password=password)
                self.account.logout()
                assert self._try_login(email=original_email, password=password), (
                    "Rollback failed: could not login with original email after restoring email."
                )
                print("[MY_ACCOUNT][EMAIL][INFO] Original email restored")

        return MyAccountCaseResult(warnings=tuple(warnings), notes=tuple(notes))

    def run_update_password_case(self) -> MyAccountCaseResult:
        warnings: list[str] = []
        notes: list[str] = []

        email = self.config.email
        original_password = self.config.password
        temporary_password = self._temporary_password()
        active_password = original_password

        print("[MY_ACCOUNT][PASSWORD][STEP] Login and open Update Password")
        try:
            self._login(email=email, password=original_password)
            self.account.open_update_password()

            self.account.submit_update_password_empty()
            errors = self.account.collect_visible_form_errors()
            lowered = " ".join(errors).lower()
            assert "required" in lowered or "enter" in lowered, (
                f"Expected mandatory validation on empty password form. errors={errors}"
            )
            print("[MY_ACCOUNT][PASSWORD][PASS] Mandatory validation is shown")

            self.account.submit_update_password(
                current_password=original_password,
                new_password=temporary_password,
            )
            notes.append("password_changed_to_temporary=true")
            print("[MY_ACCOUNT][PASSWORD][INFO] Requested password update to temporary value")

            self.account.logout()
            assert self._try_login(email=email, password=temporary_password), (
                "Could not login with temporary password after password update."
            )
            active_password = temporary_password
            print("[MY_ACCOUNT][PASSWORD][PASS] Login with temporary password works")
        finally:
            if active_password != original_password:
                restored, final_password = self._restore_original_password(
                    email=email,
                    current_password=active_password,
                    original_password=original_password,
                )
                assert restored, (
                    "Rollback failed: could not login with original password after restore. "
                    f"Account currently logs in with: {final_password}"
                )
                print("[MY_ACCOUNT][PASSWORD][INFO] Original password restored")

        return MyAccountCaseResult(warnings=tuple(warnings), notes=tuple(notes))

    def run_address_book_case(self) -> MyAccountCaseResult:
        warnings: list[str] = []
        notes: list[str] = []
        created_line1s: list[str] = []
        marker = random.randint(100000, 999999)

        edit_address = AddressData(
            first_name="Vlad",
            last_name="Ponomarenko",
            company="QA",
            line1=f"QA Auto Edit {marker} Street",
            line2="Flat 1",
            postcode="SW1A 1AA",
            town="London",
            region="",
        )
        edited_address = AddressData(
            first_name=edit_address.first_name,
            last_name=edit_address.last_name,
            company=edit_address.company,
            line1=f"QA Auto Edited {marker} Street",
            line2="Flat 2",
            postcode="SW1A 2AA",
            town="London",
            region="",
        )
        delete_address = AddressData(
            first_name="Vlad",
            last_name="Ponomarenko",
            company="QA",
            line1=f"QA Auto Delete {marker} Road",
            line2="Office",
            postcode="TR8 4XW",
            town="Newquay",
            region="",
        )
        cancel_address = AddressData(
            first_name="Vlad",
            last_name="Ponomarenko",
            company="QA",
            line1=f"QA Auto Cancel {marker} Ave",
            line2="",
            postcode="EC1A 1BB",
            town="London",
            region="",
        )
        loqate_created_line1 = ""

        print("[MY_ACCOUNT][ADDRESS][STEP] Login and open Address Book")
        self._login(email=self.config.email, password=self.config.password)
        self.account.open_address_book()

        try:
            print("[MY_ACCOUNT][ADDRESS][STEP] Add new address manually and save")
            self.account.open_add_address()
            self.account.switch_to_manual_address_mode()
            self.account.fill_address_form(edit_address)
            self.account.save_address()
            self.account.open_address_book()
            assert self.account.address_exists(edit_address.line1), "Manual address was not saved"
            created_line1s.append(edit_address.line1)
            print("[MY_ACCOUNT][ADDRESS][PASS] Manual address saved")

            print("[MY_ACCOUNT][ADDRESS][STEP] Edit existing address and verify validation")
            self.account.open_edit_address(edit_address.line1)
            self.account.switch_to_manual_address_mode()
            self.account.clear_address_required_fields()
            self.account.save_address()
            errors = self.account.collect_visible_form_errors()
            lowered = " ".join(errors).lower()
            assert "address" in lowered and "postal" in lowered and "town" in lowered, (
                f"Validation errors for mandatory address fields are missing. errors={errors}"
            )
            print("[MY_ACCOUNT][ADDRESS][PASS] Validation errors shown on edit with empty required fields")

            self.account.fill_address_form(edited_address)
            self.account.save_address()
            self.account.open_address_book()
            assert self.account.address_exists(edited_address.line1), "Edited address was not saved"
            created_line1s.remove(edit_address.line1)
            created_line1s.append(edited_address.line1)
            print("[MY_ACCOUNT][ADDRESS][PASS] Existing address edited and saved")

            print("[MY_ACCOUNT][ADDRESS][STEP] Add one more address and delete it")
            self.account.open_add_address()
            self.account.switch_to_manual_address_mode()
            self.account.fill_address_form(delete_address)
            self.account.save_address()
            self.account.open_address_book()
            assert self.account.address_exists(delete_address.line1), "Address for delete scenario was not saved"
            created_line1s.append(delete_address.line1)
            self.account.delete_address(delete_address.line1)
            self.account.open_address_book()
            assert not self.account.address_exists(delete_address.line1), "Address was not deleted"
            created_line1s.remove(delete_address.line1)
            print("[MY_ACCOUNT][ADDRESS][PASS] Existing address deleted")

            print("[MY_ACCOUNT][ADDRESS][STEP] Add address form validation for mandatory fields")
            self.account.open_add_address()
            self.account.switch_to_manual_address_mode()
            self.account.clear_address_required_fields()
            self.account.save_address()
            add_errors = self.account.collect_visible_form_errors()
            lowered = " ".join(add_errors).lower()
            assert "address" in lowered and "postal" in lowered and "town" in lowered, (
                f"Validation errors for add-address mandatory fields are missing. errors={add_errors}"
            )
            self.account.cancel_address()
            self.account.open_address_book()
            print("[MY_ACCOUNT][ADDRESS][PASS] Add-address mandatory validation works")

            print("[MY_ACCOUNT][ADDRESS][STEP] Cancel new address and ensure it is not saved")
            self.account.open_add_address()
            self.account.switch_to_manual_address_mode()
            self.account.fill_address_form(cancel_address)
            self.account.cancel_address()
            self.account.open_address_book()
            assert not self.account.address_exists(cancel_address.line1), "Canceled address should not be saved"
            print("[MY_ACCOUNT][ADDRESS][PASS] Cancel on add-address works")

            print("[MY_ACCOUNT][ADDRESS][STEP] Try Loqate postcode finder auto-population")
            self.account.open_add_address()
            loqate_seed = AddressData(
                first_name="Vlad",
                last_name="Ponomarenko",
                company="QA",
                line1="",
                line2="",
                postcode="",
                town="",
            )
            self.account.page.locator("#first-name").first.fill(loqate_seed.first_name)
            self.account.page.locator("#last-name").first.fill(loqate_seed.last_name)
            result = self.account.attempt_loqate_autofill(postcode=self.config.loqate_postcode)
            if not result.suggestions_visible:
                warnings.append(
                    "Loqate suggestions were not visible during test run. Auto-population could not be fully verified."
                )
            if not result.populated:
                warnings.append(
                    f"Loqate did not auto-populate line1/postcode/town for postcode '{self.config.loqate_postcode}'."
                )
                self.account.cancel_address()
                self.account.open_address_book()
            else:
                loqate_created_line1 = result.line1
                self.account.save_address()
                self.account.open_address_book()
                if loqate_created_line1 and self.account.address_exists(loqate_created_line1):
                    created_line1s.append(loqate_created_line1)
                    print(
                        "[MY_ACCOUNT][ADDRESS][PASS] Loqate auto-populated and saved address: "
                        f"{loqate_created_line1}"
                    )
                else:
                    warnings.append("Loqate save was attempted but created address was not found in Address Book.")

            notes.append(f"edited_address={edited_address.line1}")
            notes.append(f"loqate_autofill_populated={result.populated}")
            notes.append(f"loqate_address_line1={loqate_created_line1 or '<none>'}")
        finally:
            self.account.open_address_book()
            for line1 in list(reversed(created_line1s)):
                if self.account.address_exists(line1):
                    try:
                        self.account.delete_address(line1)
                        self.account.open_address_book()
                        print(f"[MY_ACCOUNT][ADDRESS][CLEANUP] Removed test address: {line1}")
                    except Exception as exc:
                        warnings.append(f"Cleanup failed for address '{line1}': {type(exc).__name__}")

        return MyAccountCaseResult(warnings=tuple(warnings), notes=tuple(notes))

    def _login(self, email: str, password: str, timeout: int = 60000):
        self.account.open_account_home(
            account_home_url=self.config.account_home_url,
            email=email,
            password=password,
            timeout=timeout,
        )

    def _try_login(self, email: str, password: str) -> bool:
        try:
            self._login(email=email, password=password, timeout=20000)
            return True
        except Exception:
            return False

    def _change_password_and_verify(self, email: str, current_password: str, new_password: str) -> bool:
        self._login(email=email, password=current_password, timeout=35000)
        self.account.open_update_password()
        self.account.submit_update_password(
            current_password=current_password,
            new_password=new_password,
        )
        self.account.logout()
        return self._try_login(email=email, password=new_password)

    def _restore_original_password(
        self,
        email: str,
        current_password: str,
        original_password: str,
    ) -> tuple[bool, str]:
        if self._change_password_and_verify(
            email=email,
            current_password=current_password,
            new_password=original_password,
        ):
            return True, original_password

        rolling_password = current_password
        for idx in range(1, 4):
            bridge = self._temporary_password(seed=idx + 100)
            print(f"[MY_ACCOUNT][PASSWORD][ROLLBACK] direct restore failed, rotate attempt={idx}")
            if not self._change_password_and_verify(
                email=email,
                current_password=rolling_password,
                new_password=bridge,
            ):
                return False, rolling_password
            rolling_password = bridge

            if self._change_password_and_verify(
                email=email,
                current_password=rolling_password,
                new_password=original_password,
            ):
                return True, original_password

        return False, rolling_password

    @staticmethod
    def _mutated_name(current: str, fallback: str) -> str:
        base = (current or fallback).strip()
        cleaned = re.sub(r"[^A-Za-z]", "", base) or fallback
        if cleaned.lower().endswith("qa"):
            return cleaned[:28]
        return f"{cleaned[:24]}QA"

    @staticmethod
    def _random_email_alias(base_email: str, tag: str) -> str:
        local, domain = base_email.split("@", 1)
        local_no_alias = local.split("+", 1)[0]
        suffix = random.randint(100000, 999999)
        return f"{local_no_alias}+{tag}{suffix}@{domain}"

    @staticmethod
    def _temporary_password(seed: int | None = None) -> str:
        suffix = seed if seed is not None else random.randint(100, 999)
        return f"TmpPass!A{suffix}x9"
