from __future__ import annotations

import os
import random
import re
from urllib.parse import urlsplit

import allure
import pytest

from flows.account_access_flow import AccountAccessFlow
from pages.auth_page import RegistrationUserData

SUCCESS_MESSAGE = "Account access and header navigation work correctly"
COVERED_CASE_IDS = (5, 6, 7, 8, 9)


def _base_url() -> str:
    for key in ("UI_BASE_URL", "BASE_URL", "HOME_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if not value:
            continue
        if value.endswith("/en_GB"):
            return value[: -len("/en_GB")]
        return value
    return "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com"


def _registered_credentials() -> tuple[str, str]:
    email = (
        os.getenv("STAGE_EMAIL", "").strip()
        or os.getenv("REG_EMAIL", "").strip()
        or os.getenv("REG_VLAD_EMAIL", "").strip()
        or "vlad.ponomarenko@keenethics.com"
    )
    password = (
        os.getenv("STAGE_PASSWORD", "").strip()
        or os.getenv("REG_PASS", "").strip()
        or os.getenv("REG_VLAD_PASSWORD", "").strip()
        or "Testpass111!"
    )
    return email, password


def _new_registration_email() -> str:
    suffix = random.randint(1_000_000, 9_999_999)
    return f"vlad.ponomarenko+random{suffix}@keenethics.com"


@pytest.mark.functional
@allure.title("Functional: Sign in/sign out/register and header navigation")
def test_account_access_and_header_navigation(page):
    base_url = _base_url()
    registered_email, registered_password = _registered_credentials()
    new_user_email = _new_registration_email()

    flow = AccountAccessFlow(page=page, base_url=base_url)

    with allure.step("Precondition: open homepage and accept cookies"):
        flow.open_home_and_accept_cookie()

    with allure.step("Check #1: sign in as registered user"):
        login_url = flow.sign_in_registered_user(email=registered_email, password=registered_password)
        assert "/en_GB" in login_url, f"Unexpected URL after login: {login_url}"
        print(f"[AUTH][PASS] Signed in as registered user: {registered_email}")

    with allure.step("Check #2: sign out as registered user"):
        logout_url = flow.sign_out_registered_user()
        logout_path = urlsplit(logout_url).path.rstrip("/")
        assert logout_path in ("/en_GB", "/en_GB/login"), f"Unexpected URL after sign out: {logout_url}"
        print(f"[AUTH][PASS] Signed out registered user: {registered_email}")

    with allure.step("Check #3: register as a new user"):
        new_user = RegistrationUserData(
            first_name="Vlad",
            last_name="Ponomarenko",
            email=new_user_email,
            password=registered_password,
        )
        after_register_url = flow.register_new_user(user=new_user)
        assert "/login?loggedOut=true" not in after_register_url, (
            f"Registration did not keep user signed in. url={after_register_url}"
        )
        print(f"[AUTH][PASS] Registered new user: {new_user_email}")

    with allure.step("Check #4: click basket icon and navigate to cart page"):
        cart_url = flow.open_basket_checkout_to_cart()
        assert re.search(r"/en_GB/cart(?:$|[/?#])", cart_url), f"Unexpected cart URL: {cart_url}"

    with allure.step("Check #5: click Epson logo and navigate to homepage"):
        home_url = flow.navigate_home_by_logo()
        path = urlsplit(home_url).path.rstrip("/")
        assert path == "/en_GB", f"Unexpected homepage URL after logo click: {home_url}"

    allure.attach(
        (
            f"{SUCCESS_MESSAGE}\n"
            f"covered_case_ids={','.join(map(str, COVERED_CASE_IDS))}\n"
            f"new_user_email={new_user_email}\n"
        ),
        name="Account access and navigation result",
        attachment_type=allure.attachment_type.TEXT,
    )
    print(f"[FUNCTIONAL][PASS] {SUCCESS_MESSAGE}")
