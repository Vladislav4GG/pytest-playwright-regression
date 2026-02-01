# conftest.py
import os
import pathlib
from datetime import datetime

import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from utils.config import PW_HEADLESS, PW_TIMEOUT_MS

# ✅ ВАЖЛИВО: спочатку вантажимо .env ОДИН раз
load_dotenv(dotenv_path=".env", override=False)

ARTIFACTS = pathlib.Path("artifacts")
SCREENSHOTS_DIR = ARTIFACTS / "screenshots"
TRACE_DIR = ARTIFACTS / "trace"
VIDEO_DIR = ARTIFACTS / "video"

ARTIFACTS.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
TRACE_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(s: str) -> str:
    return s.replace("::", "_").replace("/", "_").replace("\\", "_").replace(" ", "_")


@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(pw) -> Browser:
    return pw.chromium.launch(headless=PW_HEADLESS)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    1) Зберігаємо rep_call/rep_setup/rep_teardown на item (для інших fixture)
    2) Після call — робимо screenshot завжди (PASSED/FAILED)
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

    # нас цікавить саме результат тесту, не setup/teardown
    if rep.when != "call":
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    try:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        status = "PASSED" if rep.passed else "FAILED"
        test_name = _safe_name(item.nodeid)
        path = SCREENSHOTS_DIR / f"{test_name}_{status}_{ts}.png"

        # якщо сторінка закрита — не падаємо
        if not page.is_closed():
            page.screenshot(path=str(path), full_page=True)
            print(f"\n📸 Screenshot saved: {path}")
    except Exception as e:
        print(f"\n⚠️ Screenshot hook failed: {e}")


@pytest.fixture()
def context(browser: Browser, request) -> BrowserContext:
    test_name = _safe_name(request.node.name)

    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(VIDEO_DIR / test_name),
    )
    ctx.set_default_timeout(PW_TIMEOUT_MS)

    # трасу стартуємо завжди, але зберігаємо файл тільки якщо fail
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield ctx

    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed

    try:
        if failed:
            trace_path = TRACE_DIR / f"{test_name}.zip"
            ctx.tracing.stop(path=str(trace_path))
            print(f"\n🧵 Trace saved: {trace_path}")
        else:
            ctx.tracing.stop()
    finally:
        ctx.close()


@pytest.fixture()
def page(context: BrowserContext) -> Page:
    return context.new_page()