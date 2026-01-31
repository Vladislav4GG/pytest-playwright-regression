# utils/config.py
import os


def env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {name}")
    return val


# Base URLs / creds
BASE_URL = env("BASE_URL")
STAGE_EMAIL = os.getenv("STAGE_EMAIL", "")
STAGE_PASSWORD = os.getenv("STAGE_PASSWORD", "")

# Playwright
PW_HEADLESS = env("PW_HEADLESS", "true").lower() == "true"
PW_TIMEOUT_MS = int(env("PW_TIMEOUT_MS", "15000"))