"""Fetch store pages and classify a named product's availability."""

from __future__ import annotations

from selenium.common.exceptions import WebDriverException

from .browser import BrowserSession
from .detector import Availability, DetectorResult, detect_product_availability


class ProductMonitor:
    """Check a store page for one product using product-level evidence."""

    def __init__(
        self,
        url: str,
        product_name: str,
        browser_session: BrowserSession | None = None,
    ) -> None:
        self.url = url
        self.product_name = product_name
        self.browser_session = browser_session or BrowserSession()

    def check(self) -> DetectorResult:
        """Fetch the store page once and return the product stock status."""
        try:
            page_html = self.browser_session.fetch(self.url)
        except (RuntimeError, WebDriverException) as error:
            error_message = getattr(error, "msg", None) or str(error).strip()
            return DetectorResult(
                Availability.UNKNOWN,
                error_message=error_message or type(error).__name__,
            )

        return detect_product_availability(page_html, self.product_name)

    def close(self) -> None:
        """Release the browser session used by this monitor."""
        self.browser_session.close()
