from unittest.mock import MagicMock

from selenium.common.exceptions import WebDriverException

from appointment_monitor.detector import Availability
from appointment_monitor.monitor import ProductMonitor


def test_check_detects_product_with_active_order_control():
    browser = MagicMock()
    browser.fetch.return_value = """
        <article class="product-card">
          <h2>Original Glazed Dozen</h2>
          <button>Add to order</button>
        </article>
    """
    monitor = ProductMonitor(
        "https://example.com/store/order",
        "Original Glazed Dozen",
        browser,
    )

    result = monitor.check()

    browser.fetch.assert_called_once_with("https://example.com/store/order")
    assert result.availability == Availability.AVAILABLE
    assert result.evidence == "active product action"


def test_check_detects_sold_out_product():
    browser = MagicMock()
    browser.fetch.return_value = """
        <article class="product-card">
          <h2>Original Glazed Dozen</h2>
          <p>Sold out</p>
        </article>
    """
    monitor = ProductMonitor("https://example.com/order", "Original Glazed Dozen", browser)

    result = monitor.check()

    assert result.availability == Availability.UNAVAILABLE


def test_check_does_not_use_global_page_phrases():
    browser = MagicMock()
    browser.fetch.return_value = """
        <head><title>Original Glazed available</title></head>
        <script>Original Glazed Doughnut is available</script>
        <p>Original Glazed is available today.</p>
    """
    monitor = ProductMonitor("https://example.com/order", "Original Glazed", browser)

    result = monitor.check()

    assert result.availability == Availability.UNKNOWN


def test_check_returns_browser_exception_as_error():
    browser = MagicMock()
    browser.fetch.side_effect = WebDriverException("navigation timed out")
    monitor = ProductMonitor("https://example.com/order", "Original Glazed", browser)

    result = monitor.check()

    assert result.availability == Availability.UNKNOWN
    assert result.error_message == "navigation timed out"


def test_close_closes_browser_session():
    browser = MagicMock()
    monitor = ProductMonitor("https://example.com/order", "Original Glazed", browser)

    monitor.close()

    browser.close.assert_called_once_with()
