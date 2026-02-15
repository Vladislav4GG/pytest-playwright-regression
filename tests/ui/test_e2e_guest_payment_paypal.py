# tests/ui/test_e2e_guest_payment_paypal.py
import os
import pytest
import allure

from flows.purchase_flow import PurchaseFlow
from pages.confirmation_page import ConfirmationPage

PDP_URL = os.getenv("PDP_URL", "").strip()
if not PDP_URL:
    raise RuntimeError("PDP_URL env var is empty. Workflow must set it.")


def _guest_data():
    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    guest_email = os.getenv("GUEST_EMAIL", "").strip()
    if not guest_email:
        raise RuntimeError("Guest email is empty. Set GUEST_EMAIL env var.")

    paypal_email = os.getenv("PAYPAL_TEST_EMAIL", "").strip()
    paypal_pass = os.getenv("PAYPAL_TEST_PASSWORD", "").strip()
    if not paypal_email or not paypal_pass:
        raise RuntimeError("Missing PAYPAL_TEST_EMAIL/PAYPAL_TEST_PASSWORD")

    return address, guest_email, paypal_email, paypal_pass

@pytest.mark.e2e
@pytest.mark.e2e_guest
@pytest.mark.e2e_paypal
@pytest.mark.e2e_return
@allure.title("E2E (Guest): PayPal payment + Shipment API + Return flow")
def test_guest_paypal_place_order_and_return(page):
    flow = PurchaseFlow(page)
    address, guest_email, paypal_email, paypal_pass = _guest_data()

    flow.go_pdp_and_reach_billing_info_as_guest(
        pdp_url=PDP_URL,
        guest_email=guest_email,
        address=address,
    )

    flow.pay_by_paypal_and_place_order(
        paypal_email=paypal_email,
        paypal_password=paypal_pass,
    )

    result = flow.place_order_and_return_as_guest(guest_email=guest_email)
    print("RETURN RESULT:", result)

    assert result.get("shipment_status", 0) < 400, f"Shipment failed: {result}"
    assert result.get("order_code"), "No order_code in return result"
    assert result.get("sku"), "No sku in return result"