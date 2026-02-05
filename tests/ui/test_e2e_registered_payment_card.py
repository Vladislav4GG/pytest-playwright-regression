# tests/ui/test_e2e_registered_payment_card.py
import os
import pytest
import allure

from flows.purchase_flow import PurchaseFlow
from pages.confirmation_page import ConfirmationPage
from utils.shipment_api import ShipmentApiClient

PDP_INK_URL = (
    "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com"
    "/en_GB/products/ink-and-paper/ink-consumables/102-ecotank-pigment-black-ink-bottle/p/22050"
)


def _registered_data():
    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    # береться з env, щоб GitHub Actions міг підставляти
    user_email = os.getenv("STAGE_EMAIL", "").strip()
    user_password = os.getenv("STAGE_PASSWORD", "").strip()

    # якщо запускаєш локально і хочеш дефолт — можеш лишити, але краще НЕ хардкодити
    # user_email = user_email or "your_default_email@example.com"
    # user_password = user_password or "your_default_password"

    if not user_email or not user_password:
        raise RuntimeError(
            "Registered credentials are empty. Set STAGE_EMAIL and STAGE_PASSWORD env vars."
        )

    card = {
        "number": "5555 4444 3333 1111",
        "expiry": "03/30",
        "cvc": "737",
        "holder": "Vlad",
    }

    return address, user_email, user_password, card


@pytest.mark.e2e
@pytest.mark.e2e_registered
@pytest.mark.e2e_order
@allure.title("E2E (Registered): Place order with NEW credit card (no shipment/return)")
def test_registered_place_order_card_only(page):
    flow = PurchaseFlow(page)
    address, user_email, user_password, card = _registered_data()

    flow.go_pdp_and_reach_billing_info_as_registered(
        pdp_url=PDP_INK_URL,
        user_email=user_email,
        user_password=user_password,
        address=address,
    )

    flow.pay_by_card_and_place_order(card, prefer_saved=False)

    c = ConfirmationPage(page)
    order_code = c.get_order_code()
    sku = c.get_first_sku()

    assert order_code, "Order code is empty on confirmation page"
    assert sku, "SKU is empty on confirmation page"


@pytest.mark.e2e
@pytest.mark.e2e_registered
@pytest.mark.e2e_return
@allure.title("E2E (Registered): Place order + Shipment API + Return flow")
def test_registered_place_order_card_and_return(page):
    flow = PurchaseFlow(page)
    address, user_email, user_password, card = _registered_data()

    flow.go_pdp_and_reach_billing_info_as_registered(
        pdp_url=PDP_INK_URL,
        user_email=user_email,
        user_password=user_password,
        address=address,
    )

    flow.pay_by_card_and_place_order(card, prefer_saved=False)

    # 1) Confirmation
    c = ConfirmationPage(page)
    order_code = c.get_order_code()
    sku = c.get_first_sku()
    page.wait_for_timeout(10_000)

    assert order_code, "Order code is empty on confirmation page"
    assert sku, "SKU is empty on confirmation page"

    # 2) Shipment API
    api = ShipmentApiClient()
    resp = api.notify_shipment(order_ref=order_code, sku=sku, shipped_qty=1)
    assert resp.status_code < 400, f"Shipment API failed: {resp.status_code} {resp.text}"

    # 3) Registered return flow
    flow.return_order_as_registered(order_code=order_code)