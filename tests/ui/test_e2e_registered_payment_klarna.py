import os
import pytest
import allure

from flows.purchase_flow import PurchaseFlow
from pages.confirmation_page import ConfirmationPage
from utils.shipment_api import ShipmentApiClient

PDP_URL = os.getenv("PDP_URL", "").strip()
if not PDP_URL:
    raise RuntimeError("PDP_URL env var is empty. Workflow must set it.")


def _registered_data():
    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    user_email = os.getenv("REG_EMAIL", "").strip()
    user_password = os.getenv("REG_PASS", "").strip()
    if not user_email or not user_password:
        raise RuntimeError("Registered credentials are empty. Set REG_EMAIL and REG_PASS env vars.")

    return address, user_email, user_password


@pytest.mark.e2e
@pytest.mark.e2e_registered
@pytest.mark.e2e_klarna
@pytest.mark.e2e_return
@allure.title("E2E (Registered): Klarna payment + Shipment API + Return flow")
def test_registered_klarna_order_and_return(page):
    flow = PurchaseFlow(page)

    address, user_email, user_password = _registered_data()

    flow.go_pdp_and_reach_billing_info_as_registered(
        pdp_url=PDP_URL,
        user_email=user_email,
        user_password=user_password,
        address=address,
    )

    # 1) Klarna -> confirmation (метод сам повертає order_code)
    order_code = flow.pay_by_klarna_and_place_order(
        phone=os.getenv("KLARNA_PHONE", "447400123456").strip(),
        otp=os.getenv("KLARNA_OTP", "111111").strip(),
        email=os.getenv("KLARNA_EMAIL", "").strip() or None,  # None => rand email в popup page
        first_name=address["first"],
        last_name=address["last"],
        dob=os.getenv("KLARNA_DOB", "11.11.1990").strip(),
        timeout_s=int(os.getenv("KLARNA_TIMEOUT_S", "120")),
    )

    # 2) Confirmation: order_code + sku
    c = ConfirmationPage(page)
    sku = c.get_first_sku()
    page.wait_for_timeout(10_000)

    assert order_code, "Order code is empty after Klarna payment"
    assert sku, "SKU is empty on confirmation page"

    # 3) Shipment API (як у card test)
    api = ShipmentApiClient()
    resp = api.notify_shipment_with_retry(
        order_ref=order_code,
        sku=sku,
        shipped_qty=1,
        timeout_s=180,
        poll_s=10,
    )
    assert resp.status_code < 400, f"Shipment API failed: {resp.status_code} {resp.text}"

    # 4) Registered return flow
    flow.return_order_as_registered(order_code=order_code)