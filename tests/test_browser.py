from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from product_monitor.browser import BrowserSession


def test_start_session_prefers_chrome_and_sets_timeout():
    session = BrowserSession(page_load_timeout=7)
    chrome_driver = MagicMock()

    with (
        patch("product_monitor.browser.webdriver.Chrome", return_value=chrome_driver) as chrome,
        patch("product_monitor.browser.webdriver.Edge") as edge,
    ):
        driver = session.start_session()

    assert driver is chrome_driver
    chrome.assert_called_once_with(options=None)
    chrome_driver.set_page_load_timeout.assert_called_once_with(7)
    edge.assert_not_called()


def test_start_session_falls_back_to_edge_when_chrome_fails():
    session = BrowserSession()
    edge_driver = MagicMock()

    with (
        patch(
            "product_monitor.browser.webdriver.Chrome",
            side_effect=WebDriverException("Chrome unavailable"),
        ),
        patch("product_monitor.browser.webdriver.Edge", return_value=edge_driver),
    ):
        driver = session.start_session()

    assert driver is edge_driver
    edge_driver.set_page_load_timeout.assert_called_once_with(12)


def test_start_session_raises_when_all_browsers_fail():
    session = BrowserSession()

    with (
        patch(
            "product_monitor.browser.webdriver.Chrome",
            side_effect=WebDriverException("Chrome unavailable"),
        ),
        patch(
            "product_monitor.browser.webdriver.Edge",
            side_effect=WebDriverException("Edge unavailable"),
        ),
    ):
        with pytest.raises(RuntimeError, match="Could not start any supported browser"):
            session.start_session()


def test_start_session_reuses_existing_driver():
    session = BrowserSession()
    existing_driver = MagicMock()
    session._driver = existing_driver

    with (
        patch("product_monitor.browser.webdriver.Chrome") as chrome,
        patch("product_monitor.browser.webdriver.Edge") as edge,
    ):
        assert session.start_session() is existing_driver

    chrome.assert_not_called()
    edge.assert_not_called()


def test_fetch_navigates_and_returns_page_source():
    session = BrowserSession()
    driver = MagicMock()
    driver.page_source = "<html>available</html>"
    session._driver = driver

    result = session.fetch("https://example.com/products")

    driver.get.assert_called_once_with("https://example.com/products")
    assert result == "<html>available</html>"


def test_fetch_waits_for_requested_element():
    session = BrowserSession()
    driver = MagicMock()
    session._driver = driver
    locator = (By.CSS_SELECTOR, ".availability")
    expected_condition = MagicMock()

    with (
        patch("product_monitor.browser.WebDriverWait") as wait_class,
        patch(
            "product_monitor.browser.EC.presence_of_element_located",
            return_value=expected_condition,
        ) as presence_of_element_located,
    ):
        result = session.fetch("https://example.com/products", locator, 2.5)

    wait_class.assert_called_once_with(driver, 2.5)
    presence_of_element_located.assert_called_once_with(locator)
    wait_class.return_value.until.assert_called_once_with(expected_condition)
    assert result == driver.page_source


def test_fetch_reraises_webdriver_errors():
    session = BrowserSession()
    driver = MagicMock()
    driver.get.side_effect = WebDriverException("navigation failed")
    session._driver = driver

    with pytest.raises(WebDriverException, match="navigation failed"):
        session.fetch("https://example.com/products")


def test_close_quits_driver_and_clears_session():
    session = BrowserSession()
    driver = MagicMock()
    session._driver = driver

    session.close()

    driver.quit.assert_called_once_with()
    assert session._driver is None


def test_close_clears_session_even_if_quit_fails():
    session = BrowserSession()
    driver = MagicMock()
    driver.quit.side_effect = WebDriverException("quit failed")
    session._driver = driver

    session.close()

    driver.quit.assert_called_once_with()
    assert session._driver is None


def test_context_manager_closes_session():
    session = BrowserSession()
    driver = MagicMock()
    session._driver = driver

    with session as active_session:
        assert active_session is session

    driver.quit.assert_called_once_with()
    assert session._driver is None