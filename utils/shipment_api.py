# utils/shipment_api.py
import os
import uuid
import time
import datetime as dt
import requests


class ShipmentApiClient:
    """
    POST {SHIPMENT_API_URL}/odata2webservices/InboundShipment/Shipments
    Auth: Basic
    REQUIRED header (per Postman): Post-Persist-Hook: epsonShipmentPostPersistHook
    """

    def __init__(self):
        self.base_url = os.getenv(
            "SHIPMENT_API_URL",
            "https://api.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com",
        ).rstrip("/")

        self.user = os.getenv("SHIPMENT_API_USER")
        self.password = os.getenv("SHIPMENT_API_PASSWORD")
        self.integration_key = os.getenv("SHIPMENT_INTEGRATION_KEY")

        # з Postman
        self.post_persist_hook = os.getenv(
            "SHIPMENT_POST_PERSIST_HOOK",
            "epsonShipmentPostPersistHook",
        )

        if not self.user or not self.password or not self.integration_key:
            raise RuntimeError(
                "Shipment API env vars missing. Need SHIPMENT_API_USER, SHIPMENT_API_PASSWORD, SHIPMENT_INTEGRATION_KEY"
            )

    @staticmethod
    def _shipped_date() -> str:
        # максимально сумісно з постманом: "YYYY-MM-DDTHH:MM:SS"
        # (без timezone offset)
        return dt.datetime.utcnow().replace(microsecond=0).isoformat()

    def notify_shipment(self, order_ref: str, sku: str, shipped_qty: int = 1) -> requests.Response:
        url = f"{self.base_url}/odata2webservices/InboundShipment/Shipments"

        payload = {
            "shippedDate": self._shipped_date(),
            "orderRef": order_ref,
            "shipmentID": "demo-1",
            "entries": [
                {
                    "sku": sku,
                    "shippedQuantity": int(shipped_qty),
                    "integrationKey": self.integration_key,
                }
            ],
            "trackingRefs": [
                {
                    "url": "trackref4",
                    "reference": "trackref4",
                    "integrationKey": self.integration_key,
                }
            ],
            "integrationKey": self.integration_key,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Post-Persist-Hook": self.post_persist_hook,
        }

        print(f"[ShipmentAPI] POST {url}")
        print(f"[ShipmentAPI] hook = {self.post_persist_hook}")
        print(f"[ShipmentAPI] payload.orderRef = {order_ref}, sku = {sku}, qty = {shipped_qty}")

        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(self.user, self.password),
            timeout=30,
        )

        print(f"[ShipmentAPI] status = {resp.status_code}")
        print(f"[ShipmentAPI] text = {resp.text[:1000]}")

        return resp
    
    def notify_shipment_with_retry(self, *, order_ref: str, sku: str, shipped_qty: int = 1, timeout_s: int = 180, poll_s: int = 10):
        deadline = time.time() + timeout_s
        last = None

        while time.time() < deadline:
            resp = self.notify_shipment(order_ref=order_ref, sku=sku, shipped_qty=shipped_qty)
            last = resp

            if resp.status_code < 400:
                return resp

            txt = (resp.text or "").lower()
            if resp.status_code == 400 and "order not found in commerce" in txt:
                time.sleep(poll_s)
                continue

            return resp

        return last