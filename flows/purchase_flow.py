import re
import os
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
from pages.my_account_orders_page import MyAccountOrdersPage
from pages.order_details_registered_page import OrderDetailsRegisteredPage
import time


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
                ui_base = os.getenv("UI_BASE_URL", "").rstrip("/")
                self.page.goto(f"{ui_base}/en_GB/cart")

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

    def pay_by_card_and_place_order(self, card: dict, *, prefer_saved: bool = True):
        expect(self.page).to_have_url(re.compile(r".*/adyen/select-payment-method.*"))

        p = PaymentMethodPage(self.page)

        mode = p.select_credit_card(prefer_saved=prefer_saved)  # ← ВАЖЛИВО

        p.fill_card(
            mode=mode,
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


    def return_order_as_registered(self, *, order_code: str) -> dict:
        # ти вже залогінений як registered

        # чекаємо поки бек реально дозволить return
        self.page.wait_for_timeout(5000)
        self._wait_return_available(order_code, timeout_s=180, poll_s=5)

        r = ReturnOrderPage(self.page)
        r.confirm_return_three_steps()
        return {"order_code": order_code}

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
    
    def _goto(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        dismiss_onetrust(self.page)

    def _reach_billing_info(self, address: dict):
        self.page.wait_for_url("**/checkout/multi/delivery-address/**", timeout=20000)
        DeliveryAddressPage(self.page).fill_and_continue(
            first=address["first"],
            last=address["last"],
            line1=address["line1"],
            town=address["town"],
            postcode=address["postcode"],
        )

        self.page.wait_for_url("**/checkout/multi/delivery-method/**", timeout=20000)
        DeliveryMethodPage(self.page).next()

        self.page.wait_for_url("**/checkout/multi/billing-information/**", timeout=20000)
        BillingInfoPage(self.page).fill_and_continue_non_business(
            first=address["first"],
            last=address["last"],
            line1=address["line1"],
            town=address["town"],
            postcode=address["postcode"],
        )

        return {"final_url": self.page.url}
    
    def go_pdp_and_reach_billing_info_as_registered(
        self,
        *,
        pdp_url: str,
        user_email: str,
        user_password: str,
        address: dict,
    ):
        self._goto(pdp_url)
        PDPPage(self.page).buy_now()

        try:
            self.page.wait_for_url("**/cart**", timeout=10000)
        except Exception:
            checkout_btn = self.page.get_by_role("button", name="Checkout")
            if checkout_btn.is_visible():
                checkout_btn.click()
            else:
                self._goto(f"{self.page.url.split('/en_GB')[0]}/en_GB/cart")

        dismiss_onetrust(self.page)
        CartPage(self.page).click_checkout()

        # registered path: log in (і тільки якщо ми реально на checkout login)
        if "/login/checkout" in self.page.url:
            dismiss_onetrust(self.page)
            CheckoutLoginPage(self.page).login(email=user_email, password=user_password)

        return self._reach_billing_info(address)
    
    def _wait_return_available(self, order_code: str, timeout_s: int = 120, poll_s: int = 5):
        """
        Чекаємо поки /returns реально відкривається без фейлу.
        Це прибирає флапи через асинхронний бек-процесинг після Shipment API.
        """
        ui_base = os.getenv("UI_BASE_URL", "").rstrip("/")
        url_returns = f"{ui_base}/en_GB/customer/order/{order_code}/returns"
        deadline = time.time() + timeout_s
        last_url = None

        while time.time() < deadline:
            self.page.goto(url_returns, wait_until="domcontentloaded", timeout=45000)
            last_url = self.page.url

            # 1) якщо нас редіректнуло — значить ще не готово
            if "/customer/order/" not in last_url or "/returns" not in last_url:
                time.sleep(poll_s)
                continue

            # 2) якщо є банер помилки — ще не готово
            error_banner = self.page.locator("text=Something went wrong").first
            if error_banner.count() > 0 and error_banner.is_visible():
                time.sleep(poll_s)
                continue

            # 3) ключове: на returns-сторінці має з’явитись кнопка confirm (або заголовок)
            confirm = self.page.get_by_role("button", name=re.compile(r"confirm", re.I))
            if confirm.count() > 0 and confirm.first.is_visible():
                return

            time.sleep(poll_s)

        raise AssertionError(f"Return page not ready for order {order_code}. Last url={last_url}")