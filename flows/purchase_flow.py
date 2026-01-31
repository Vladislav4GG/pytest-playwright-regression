import re
from playwright.sync_api import Page, expect
from utils.consent import dismiss_onetrust
from pages.pdp_page import PDPPage
from pages.cart_page import CartPage
from pages.checkout_login_page import CheckoutLoginPage
from pages.delivery_address_page import DeliveryAddressPage
from pages.delivery_method_page import DeliveryMethodPage
from pages.billing_info_page import BillingInfoPage
from pages.payment_method_page import PaymentMethodPage
from pages.summary_page import SummaryPage
from pages.confirmation_page import ConfirmationPage
from pages.guest_order_lookup_page import GuestOrderLookupPage
from pages.order_details_page import OrderDetailsPage
from pages.return_order_page import ReturnOrderPage
from utils.shipment_api import ShipmentApiClient


class PurchaseFlow:
    def __init__(self, page: Page):
        self.page = page

    def go_pdp_and_reach_billing_info_as_guest(self, pdp_url: str, guest_email: str, address: dict):
        self.page.goto(pdp_url)
        dismiss_onetrust(self.page)
        PDPPage(self.page).buy_now()

        try:
            self.page.wait_for_url("**/cart**", timeout=8000)
        except Exception:
            checkout_btn = self.page.get_by_role("button", name="Checkout")
            if checkout_btn.is_visible():
                checkout_btn.click()
            else:
                self.page.goto(
                    "https://epson-gb.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com/en_GB/cart"
                )

        dismiss_onetrust(self.page)
        CartPage(self.page).click_checkout()

        if "/login/checkout" in self.page.url:
            dismiss_onetrust(self.page)
            CheckoutLoginPage(self.page).checkout_as_guest(guest_email)

        self.page.wait_for_url("**/checkout/multi/delivery-address/**", timeout=15000)
        DeliveryAddressPage(self.page).fill_and_continue(
            first=address["first"],
            last=address["last"],
            line1=address["line1"],
            town=address["town"],
            postcode=address["postcode"],
        )

        self.page.wait_for_url("**/checkout/multi/delivery-method/**", timeout=15000)
        DeliveryMethodPage(self.page).next()

        self.page.wait_for_url("**/checkout/multi/billing-information/**", timeout=15000)
        BillingInfoPage(self.page).fill_and_continue_non_business(
            first=address["first"],
            last=address["last"],
            line1=address["line1"],
            town=address["town"],
            postcode=address["postcode"],
        )

        return {"final_url": self.page.url}

    def pay_by_card_and_place_order(self, card: dict):
        expect(self.page).to_have_url(re.compile(r".*/adyen/select-payment-method.*"))

        p = PaymentMethodPage(self.page)
        p.select_credit_card()
        p.fill_card(
            number=card["number"],
            expiry=card["expiry"],
            cvc=card["cvc"],
            holder=card["holder"],
        )
        p.click_next()

        expect(self.page).to_have_url(re.compile(r".*/adyen/summary/view.*"), timeout=20000)

        s = SummaryPage(self.page)
        s.accept_terms()
        s.place_order()

    def place_order_and_return_as_guest(self, guest_email: str) -> dict:
        """
        Викликати ПІСЛЯ pay_by_card_and_place_order().
        1) На confirmation беремо order_code + sku
        2) Шлем Shipment API
        3) Йдемо в guest lookup, відкриваємо order
        4) Return Order + 3 confirm
        """
        # 1) Confirmation: витягуємо order_code + sku
        c = ConfirmationPage(self.page)
        order_code = c.get_order_code()
        sku = c.get_first_sku()
        self.page.wait_for_timeout(10000)

        # 2) Shipment API
        api = ShipmentApiClient()
        resp = api.notify_shipment(order_ref=order_code, sku=sku, shipped_qty=1)
        if resp.status_code >= 400:
            raise AssertionError(
                f"Shipment API failed: {resp.status_code} {resp.text}"
            )

        # 3) Guest lookup
        g = GuestOrderLookupPage(self.page)
        g.open()
        dismiss_onetrust(self.page)
        g.retrieve_order(email=guest_email, order_code=order_code)

        # 4) Order details -> Return Order
        od = OrderDetailsPage(self.page)
        od.wait_loaded()
        # Перевіримо, що SKU той самий (опційно, але корисно)
        sku_ui = od.get_first_sku()
        if sku_ui != sku:
            raise AssertionError(f"SKU mismatch. confirmation={sku}, order_details={sku_ui}")

        od.click_return_order()

        # 5) 3x confirm
        r = ReturnOrderPage(self.page)
        r.confirm_return_three_steps()

        return {"order_code": order_code, "sku": sku, "shipment_status": resp.status_code}