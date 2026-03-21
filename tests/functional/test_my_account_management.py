from __future__ import annotations

import os

import allure
import pytest

from flows.my_account_flow import MyAccountCaseResult, MyAccountConfig, MyAccountFlow


def _test_env() -> str:
    raw = os.getenv("TEST_ENV", "S1").strip().upper()
    return "S2" if raw == "S2" else "S1"


def _base_url() -> str:
    for key in ("UI_BASE_URL", "BASE_URL", "HOME_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if not value:
            continue
        if value.endswith("/en_GB"):
            return value[: -len("/en_GB")]
        return value
    suffix = "s2" if _test_env() == "S2" else "s1"
    return f"https://epson-gb.cbnd-seikoepso3-{suffix}-public.model-t.cc.commerce.ondemand.com"


def _credentials() -> tuple[str, str]:
    email = (
        os.getenv("MY_ACCOUNT_EMAIL", "").strip()
        or os.getenv("REG_VLAD_EMAIL", "").strip()
        or os.getenv("STAGE_EMAIL", "").strip()
        or os.getenv("REG_EMAIL", "").strip()
        or "vlad.ponomarenko@keenethics.com"
    )
    password = (
        os.getenv("MY_ACCOUNT_PASSWORD", "").strip()
        or os.getenv("REG_VLAD_PASSWORD", "").strip()
        or os.getenv("STAGE_PASSWORD", "").strip()
        or os.getenv("REG_PASS", "").strip()
        or "Testpass111!"
    )
    return email, password


def _config() -> MyAccountConfig:
    base_url = _base_url()
    email, password = _credentials()
    return MyAccountConfig(
        base_url=base_url,
        account_home_url=f"{base_url}/en_GB/my-account/home",
        email=email,
        password=password,
        loqate_postcode=os.getenv("MY_ACCOUNT_LOQATE_POSTCODE", "SW1A 1AA").strip(),
    )


def _attach_result(title: str, result: MyAccountCaseResult):
    lines = [title]
    if result.notes:
        lines.append("notes:")
        lines.extend(f"- {item}" for item in result.notes)
    if result.warnings:
        lines.append("warnings:")
        lines.extend(f"- {item}" for item in result.warnings)
    else:
        lines.append("warnings: none")
    allure.attach("\n".join(lines), name=title, attachment_type=allure.attachment_type.TEXT)


@pytest.mark.functional
@pytest.mark.account
@allure.title("Functional: My Account - Order History")
def test_my_account_order_history(page):
    flow = MyAccountFlow(page=page, config=_config())
    result = flow.run_order_history_case()
    _attach_result("Order history result", result)
    print("[MY_ACCOUNT][ORDER][PASS] Order History flow completed")
    if result.warnings:
        for warning in result.warnings:
            print(f"[MY_ACCOUNT][ORDER][WARN] {warning}")


@pytest.mark.functional
@pytest.mark.account
@allure.title("Functional: My Account - Update Personal Details")
def test_my_account_update_personal_details(page):
    flow = MyAccountFlow(page=page, config=_config())
    result = flow.run_update_personal_details_case()
    _attach_result("Update personal details result", result)
    print("[MY_ACCOUNT][PROFILE][PASS] Update Personal Details flow completed")
    if result.warnings:
        for warning in result.warnings:
            print(f"[MY_ACCOUNT][PROFILE][WARN] {warning}")


@pytest.mark.functional
@pytest.mark.account
@allure.title("Functional: My Account - Update Email Address")
def test_my_account_update_email_address(page):
    flow = MyAccountFlow(page=page, config=_config())
    result = flow.run_update_email_case()
    _attach_result("Update email result", result)
    print("[MY_ACCOUNT][EMAIL][PASS] Update Email flow completed")
    if result.warnings:
        for warning in result.warnings:
            print(f"[MY_ACCOUNT][EMAIL][WARN] {warning}")


@pytest.mark.functional
@pytest.mark.account
@allure.title("Functional: My Account - Update Password")
def test_my_account_update_password(page):
    flow = MyAccountFlow(page=page, config=_config())
    result = flow.run_update_password_case()
    _attach_result("Update password result", result)
    print("[MY_ACCOUNT][PASSWORD][PASS] Update Password flow completed")
    if result.warnings:
        for warning in result.warnings:
            print(f"[MY_ACCOUNT][PASSWORD][WARN] {warning}")


@pytest.mark.functional
@pytest.mark.account
@allure.title("Functional: My Account - Address Book")
def test_my_account_address_book(page):
    flow = MyAccountFlow(page=page, config=_config())
    result = flow.run_address_book_case()
    _attach_result("Address book result", result)
    print("[MY_ACCOUNT][ADDRESS][PASS] Address Book flow completed")
    if result.warnings:
        for warning in result.warnings:
            print(f"[MY_ACCOUNT][ADDRESS][WARN] {warning}")
