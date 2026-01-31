import pathlib
import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from utils.config import PW_HEADLESS, PW_TIMEOUT_MS

ARTIFACTS = pathlib.Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(pw) -> Browser:
    return pw.chromium.launch(headless=PW_HEADLESS)

@pytest.fixture()
def context(browser: Browser, request) -> BrowserContext:
    test_name = request.node.name.replace("/", "_")
    video_dir = ARTIFACTS / "video" / test_name
    video_dir.mkdir(parents=True, exist_ok=True)

    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(video_dir),
    )
    ctx.set_default_timeout(PW_TIMEOUT_MS)
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield ctx

    trace_path = ARTIFACTS / "trace" / f"{test_name}.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    ctx.tracing.stop(path=str(trace_path))
    ctx.close()

@pytest.fixture()
def page(context: BrowserContext) -> Page:
    page = context.new_page()

    # OneTrust cookie consent часто блокує кліки overlay-ем.
    # Пытаємось закрити/прийняти, якщо банер з'явився.
    try:
        # 1) якщо є кнопка Accept all
        accept = page.get_by_role("button", name="Accept All Cookies")
        if accept.is_visible():
            accept.click()
        else:
            # 2) альтернативний OneTrust селектор (часто стабільний)
            btn = page.locator("#onetrust-accept-btn-handler")
            if btn.is_visible():
                btn.click()
            else:
                # 3) якщо відкрилась preferences modal - закриваємо overlay
                close = page.get_by_role("button", name="Close")
                if close.is_visible():
                    close.click()
    except Exception:
        # якщо банера нема — ок
        pass

    return page
