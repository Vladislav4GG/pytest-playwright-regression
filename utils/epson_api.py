import os
from datetime import datetime, timezone
import requests


INBOUND_SHIPMENT_URL = (
    "https://api.cbnd-seikoepso3-s1-public.model-t.cc.commerce.ondemand.com"
    "/odata2webservices/InboundShipment/Shipments"
)


def send_shipment_notification(order_ref: str, sku: str, shipped_qty: int = 1) -> requests.Response:
    """
    Calls InboundShipment/Shipments (Shipment Notification) to mark order as shipped,
    which enables return flow in UI (per your system behavior).

    Required env vars:
      - SHIPMENT_API_USER
      - SHIPMENT_API_PASSWORD
      - SHIPMENT_INTEGRATION_KEY
    Optional:
      - SHIPMENT_API_URL (override endpoint)
    """
    user = os.getenv("SHIPMENT_API_USER")
    pwd = os.getenv("SHIPMENT_API_PASSWORD")
    integration_key = os.getenv("SHIPMENT_INTEGRATION_KEY")
    url = os.getenv("SHIPMENT_API_URL", INBOUND_SHIPMENT_URL)

    if not user or not pwd:
        raise RuntimeError("Missing SHIPMENT_API_USER / SHIPMENT_API_PASSWORD in env/.env")
    if not integration_key:
        raise RuntimeError("Missing SHIPMENT_INTEGRATION_KEY in env/.env")

    shipped_date = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    payload = {
        "shippedDate": shipped_date,
        "orderRef": order_ref,
        "shipmentID": f"auto-{order_ref}",
        "entries": [
            {
                "sku": sku,
                "shippedQuantity": shipped_qty,
                "integrationKey": integration_key,
            }
        ],
        "trackingRefs": [
            {
                "url": "Test_url",
                "reference": f"track-{order_ref}",
                "integrationKey": integration_key,
            }
        ],
        "integrationKey": integration_key,
    }

    headers = {
        "Post-Persist-Hook": "epsonShipmentPostPersistHook",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, auth=(user, pwd), headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise AssertionError(
            f"Shipment API failed: {resp.status_code}\n"
            f"Response: {resp.text}"
        )
    return resp