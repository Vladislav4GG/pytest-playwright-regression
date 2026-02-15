# tests/ui/test_e2e_guest_payment_klarna.py
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

    klarna_phone = os.getenv("KLARNA_PHONE", "447400123456").strip()
    klarna_otp = os.getenv("KLARNA_OTP", "111111").strip()
    klarna_email = os.getenv("KLARNA_EMAIL", "").strip() or None
    klarna_dob = os.getenv("KLARNA_DOB", "11.11.1990").strip()
    klarna_timeout_s = int(os.getenv("KLARNA_TIMEOUT_S", "120"))

    return (
        address,
        guest_email,
        klarna_phone,
        klarna_otp,
        klarna_email,
        klarna_dob,
        klarna_timeout_s,
    )

@pytest.mark.e2e
@pytest.mark.e2e_guest
@pytest.mark.e2e_klarna
@pytest.mark.e2e_return
@allure.title("E2E (Guest): Klarna payment + Shipment API + Return flow")
def test_guest_klarna_place_order_and_return(page):
    flow = PurchaseFlow(page)
    (
        address,
        guest_email,
        phone,
        otp,
        k_email,
        dob,
        timeout_s,
    ) = _guest_data()

    flow.go_pdp_and_reach_billing_info_as_guest(
        pdp_url=PDP_URL,
        guest_email=guest_email,
        address=address,
    )

    flow.pay_by_klarna_and_place_order(
        phone=phone,
        otp=otp,
        email=k_email,
        first_name=address["first"],
        last_name=address["last"],
        dob=dob,
        timeout_s=timeout_s,
    )

    result = flow.place_order_and_return_as_guest(guest_email=guest_email)
    print("RETURN RESULT:", result)

    assert result.get("shipment_status", 0) < 400, f"Shipment failed: {result}"
    assert result.get("order_code"), "No order_code in return result"
    assert result.get("sku"), "No sku in return result"