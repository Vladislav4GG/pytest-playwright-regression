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

    user_email = os.getenv("STAGE_EMAIL", "").strip()
    user_password = os.getenv("STAGE_PASSWORD", "").strip()
    if not user_email or not user_password:
        raise RuntimeError("Registered credentials are empty. Set REG_EMAIL and REG_PASS env vars.")

    return address, user_email, user_password


@pytest.mark.e2e
@pytest.mark.e2e_registered
@pytest.mark.e2e_paypal
@pytest.mark.e2e_return
@allure.title("E2E (Registered): PayPal payment + Shipment API + Return flow")
def test_registered_paypal_order_and_return(page):
    flow = PurchaseFlow(page)

    paypal_email = os.getenv("PAYPAL_TEST_EMAIL", "").strip()
    paypal_pass = os.getenv("PAYPAL_TEST_PASSWORD", "").strip()
    if not paypal_email or not paypal_pass:
        raise RuntimeError("Missing PAYPAL_TEST_EMAIL/PAYPAL_TEST_PASSWORD")

    address, user_email, user_password = _registered_data()

    flow.go_pdp_and_reach_billing_info_as_registered(
        pdp_url=PDP_URL,
        user_email=user_email,
        user_password=user_password,
        address=address,
    )

    # 1) PayPal -> confirmation
    flow.pay_by_paypal_and_place_order(paypal_email=paypal_email, paypal_password=paypal_pass)

    # 2) Confirmation: order_code + sku
    c = ConfirmationPage(page)
    order_code = c.get_order_code()
    sku = c.get_first_sku()
    page.wait_for_timeout(10_000)

    assert order_code, "Order code is empty on confirmation page"
    assert sku, "SKU is empty on confirmation page"

    # 3) Shipment API (як у card test)
    api = ShipmentApiClient()
    resp = api.notify_shipment_with_retry(
        order_ref=order_code, sku=sku, shipped_qty=1, timeout_s=180, poll_s=10
    )
    assert resp.status_code < 400, f"Shipment API failed: {resp.status_code} {resp.text}"

    # 4) Registered return flow (вже є в PurchaseFlow)
    flow.return_order_as_registered(order_code=order_code)