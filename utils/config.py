# utils/config.py
import os


def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or str(v).strip() == "":
        raise RuntimeError(f"Missing env var: {name}")
    return v

UI_BASE_URL = env("UI_BASE_URL")
API_BASE_URL = os.getenv("API_BASE_URL", UI_BASE_URL)
PW_HEADLESS = os.getenv("PW_HEADLESS", "true").lower() == "true"
PW_TIMEOUT_MS = int(os.getenv("PW_TIMEOUT_MS", "15000"))


# Base URLs / creds
STAGE_EMAIL = os.getenv("STAGE_EMAIL", "")
STAGE_PASSWORD = os.getenv("STAGE_PASSWORD", "")

# Playwright
PW_HEADLESS = env("PW_HEADLESS", "true").lower() == "true"
PW_TIMEOUT_MS = int(env("PW_TIMEOUT_MS", "15000"))