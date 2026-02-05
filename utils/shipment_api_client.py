import os
import json
import requests


class ShipmentApiClient:
    """
    Мінімальний клієнт для shipment/return API.

    Вимоги:
      - SHIPMENT_API_USER
      - SHIPMENT_API_PASSWORD
      - SHIPMENT_INTEGRATION_KEY
      - (опційно) SHIPMENT_API_BASE_URL
    """

    def __init__(self):
        self.base_url = os.getenv("SHIPMENT_API_URL", "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("SHIPMENT_API_URL is missing. Workflow must set it (S1/S2).")
        self.user = os.getenv("SHIPMENT_API_USER")
        self.password = os.getenv("SHIPMENT_API_PASSWORD")
        self.integration_key = os.getenv("SHIPMENT_INTEGRATION_KEY")

        if not self.user or not self.password or not self.integration_key:
            raise RuntimeError("Missing SHIPMENT_API_* env vars (.env not loaded?)")

        if not self.base_url:
            # якщо ти не задав базовий URL — ми підставимо пізніше з постмана або явно в .env
            # але краще одразу додай його в .env щоб не гадати.
            pass

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            # назва хедера може відрізнятися — ми звіримо з твоїм postman
            "integration-key": self.integration_key,
        }

    def post(self, path: str, payload: dict) -> requests.Response:
        if not self.base_url:
            raise RuntimeError("SHIPMENT_API_BASE_URL is not set in .env")

        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.post(
            url,
            headers=self._headers(),
            auth=(self.user, self.password),
            data=json.dumps(payload),
            timeout=30,
        )
        return resp