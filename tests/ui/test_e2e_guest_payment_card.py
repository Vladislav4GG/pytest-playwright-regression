# tests/ui/test_e2e_guest_payment_card.py
import pytest
import allure

from flows.purchase_flow import PurchaseFlow
from pages.confirmation_page import ConfirmationPage

PDP_INK_URL = (
    "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com"
    "/en_GB/products/ink-and-paper/ink-consumables/102-ecotank-pigment-black-ink-bottle/p/22050"
)


def _guest_data():
    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    guest_email = "vlad.ponomarenko@keenethics.com"

    card = {
        "number": "5555 4444 3333 1111",
        "expiry": "03/30",
        "cvc": "737",
        "holder": "Vlad",
    }

    return address, guest_email, card


@pytest.mark.e2e
@pytest.mark.e2e_guest
@pytest.mark.e2e_order
@allure.title("E2E (Guest): Place order with credit card (no shipment/return)")
def test_guest_place_order_card_only(page):
    flow = PurchaseFlow(page)
    address, guest_email, card = _guest_data()

    flow.go_pdp_and_reach_billing_info_as_guest(
        pdp_url=PDP_INK_URL,
        guest_email=guest_email,
        address=address,
    )

    flow.pay_by_card_and_place_order(card)

    c = ConfirmationPage(page)
    order_code = c.get_order_code()
    sku = c.get_first_sku()

    assert order_code, "Order code is empty on confirmation page"
    assert sku, "SKU is empty on confirmation page"


@pytest.mark.e2e
@pytest.mark.e2e_guest_return
@pytest.mark.e2e_return
@allure.title("E2E (Guest): Place order + Shipment API + Return flow")
def test_guest_place_order_card_and_return(page):
    flow = PurchaseFlow(page)
    address, guest_email, card = _guest_data()

    flow.go_pdp_and_reach_billing_info_as_guest(
        pdp_url=PDP_INK_URL,
        guest_email=guest_email,
        address=address,
    )

    flow.pay_by_card_and_place_order(card)

    result = flow.place_order_and_return_as_guest(guest_email=guest_email)
    print("RETURN RESULT:", result)

    assert result.get("shipment_status", 0) < 400, f"Shipment failed: {result}"
    assert result.get("order_code"), "No order_code in return result"
    assert result.get("sku"), "No sku in return result"