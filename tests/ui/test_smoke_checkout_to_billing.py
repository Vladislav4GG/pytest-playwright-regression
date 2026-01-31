import pytest
import allure
from flows.purchase_flow import PurchaseFlow

PDP_INK_URL = "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/products/ink-and-paper/ink-consumables/102-ecotank-pigment-black-ink-bottle/p/22050"

@pytest.mark.smoke
@allure.title("Smoke_01: Guest checkout up to Billing Information (no payment)")
def test_guest_checkout_to_billing(page):
    flow = PurchaseFlow(page)

    address = {
        "first": "Vlad",
        "last": "Ponomarenko",
        "line1": "2 Garth Morgana An Fe",
        "town": "Newquay",
        "postcode": "TR8 4XW",
    }

    result = flow.go_pdp_and_reach_billing_info_as_guest(
        pdp_url=PDP_INK_URL,
        guest_email="vlad.autotest+guest@example.com",
        address=address
    )

    assert result["final_url"]
    # Мінімальний assert: ми вже НЕ на delivery-method
    assert "billing-information" not in result["final_url"]  # після Save and Continue має піти далі