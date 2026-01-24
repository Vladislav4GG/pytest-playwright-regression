import pytest
import allure
from utils.config import BASE_URL

@pytest.mark.smoke
@allure.title("Smoke: Open home page")
def test_open_home(page):
    page.goto(BASE_URL)
    assert page.url.startswith(BASE_URL)
