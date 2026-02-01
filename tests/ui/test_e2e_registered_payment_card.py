import pytest
import allure

from pages.confirmation_page import ConfirmationPage
from utils.shipment_api import ShipmentApiClient
from flows.purchase_flow import PurchaseFlow

PDP_INK_URL = "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/products/ink-and-paper/ink-consumables/102-ecotank-pigment-black-ink-bottle/p/22050"


@pytest.mark.e2e
@allure.title("E2E: Registered checkout with credit card (NEW card only)")
def test_registered_place_order_card_new(page):
    flow = PurchaseFlow(page)

    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    user_email = "vlad.ponomarenko@keenethics.com"
    user_password = "Testpass111!"

    card = {
        "number": "5555 4444 3333 1111",
        "expiry": "03/30",
        "cvc": "737",
        "holder": "Vlad",
    }

    flow.go_pdp_and_reach_billing_info_as_registered(
        pdp_url=PDP_INK_URL,
        user_email=user_email,
        user_password=user_password,
        address=address,
    )

    # ПОКИ ЩО — просто виклик, далі ми його підженемо
    flow.pay_by_card_and_place_order(card, prefer_saved=False)

    # 1) Confirmation
    c = ConfirmationPage(page)
    order_code = c.get_order_code()
    sku = c.get_first_sku()

    # 2) Shipment API (як у guest)
    api = ShipmentApiClient()
    resp = api.notify_shipment(order_ref=order_code, sku=sku, shipped_qty=1)
    assert resp.status_code < 400

    # 3) Registered return flow
    flow.return_order_as_registered(order_code=order_code)
