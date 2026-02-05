import os
import time
import uuid
import json
import datetime as dt
import requests


class ShipmentApiClient:
    """
    Shipment / Return API client.

    REQUIRED env vars:
      - SHIPMENT_API_URL          (S1 / S2, задається з workflow)
      - SHIPMENT_API_USER
      - SHIPMENT_API_PASSWORD
      - SHIPMENT_INTEGRATION_KEY

    OPTIONAL:
      - SHIPMENT_POST_PERSIST_HOOK (якщо використовується)
    """

    def __init__(self):
        self.base_url = os.getenv("SHIPMENT_API_URL", "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("Missing env var: SHIPMENT_API_URL")

        self.user = os.getenv("SHIPMENT_API_USER")
        self.password = os.getenv("SHIPMENT_API_PASSWORD")
        self.integration_key = os.getenv("SHIPMENT_INTEGRATION_KEY")

        if not self.user or not self.password or not self.integration_key:
            raise RuntimeError(
                "Missing Shipment API credentials. "
                "Need SHIPMENT_API_USER, SHIPMENT_API_PASSWORD, SHIPMENT_INTEGRATION_KEY"
            )

        # якщо Postman вимагає цей хедер
        self.post_persist_hook = os.getenv(
            "SHIPMENT_POST_PERSIST_HOOK",
            "epsonShipmentPostPersistHook",
        )

    # ---------- helpers ----------

    @staticmethod
    def _now_utc_iso() -> str:
        """
        ISO-8601 UTC timestamp без deprecated utcnow()
        """
        return (
            dt.datetime.now(dt.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # деякі середовища очікують цей хедер
        if self.post_persist_hook:
            headers["Post-Persist-Hook"] = self.post_persist_hook

        return headers

    # ---------- low-level ----------

    def _post(self, path: str, payload: dict) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.post(
            url,
            headers=self._headers(),
            auth=(self.user, self.password),
            json=payload,
            timeout=30,
        )
        return resp

    # ---------- public API ----------

    def notify_shipment(
        self,
        *,
        order_ref: str,
        sku: str,
        shipped_qty: int = 1,
        shipment_id: str | None = None,
    ) -> requests.Response:
        """
        One-shot shipment call (без retry).
        """
        shipment_id = shipment_id or f"demo-{uuid.uuid4().hex[:8]}"

        payload = {
            "shippedDate": self._now_utc_iso(),
            "orderRef": order_ref,
            "shipmentID": shipment_id,
            "entries": [
                {
                    "sku": sku,
                    "shippedQuantity": int(shipped_qty),
                    "integrationKey": self.integration_key,
                }
            ],
            "trackingRefs": [
                {
                    "url": "trackref",
                    "reference": "trackref",
                    "integrationKey": self.integration_key,
                }
            ],
            "integrationKey": self.integration_key,
        }

        print(
            f"[ShipmentAPI] POST order={order_ref} sku={sku} qty={shipped_qty} shipmentID={shipment_id}"
        )

        resp = self._post(
            "/odata2webservices/InboundShipment/Shipments",
            payload,
        )

        print(f"[ShipmentAPI] status={resp.status_code}")
        print(f"[ShipmentAPI] body={resp.text[:800]}")

        return resp

    def notify_shipment_with_retry(
        self,
        *,
        order_ref: str,
        sku: str,
        shipped_qty: int = 1,
        timeout_s: int = 180,
        poll_s: int = 10,
    ) -> requests.Response:
        """
        Retry ONLY when commerce has not indexed the order yet.
        This fixes S2 eventual consistency.
        """
        deadline = time.time() + timeout_s
        last_resp: requests.Response | None = None

        while time.time() < deadline:
            resp = self.notify_shipment(
                order_ref=order_ref,
                sku=sku,
                shipped_qty=shipped_qty,
            )
            last_resp = resp

            if resp.status_code < 400:
                return resp

            body = (resp.text or "").lower()
            if resp.status_code == 400 and "order not found in commerce" in body:
                print("[ShipmentAPI] Order not indexed yet, retrying...")
                time.sleep(poll_s)
                continue

            # будь-яка інша помилка — це реальний фейл
            return resp

        return last_resp