'''
This module contains functions and classes for interacting with the web browser
to monitor product availability.
'''
from __future__ import annotations

import logging
import platform

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

class BrowserSession:

    """Manage a browser session, preferring Chrome, otherwise Edge."""

    def __init__(self, page_load_timeout: int = 12) -> None:
        """Create a session that starts its browser on first use."""
        self._driver: WebDriver | None = None
        self.page_load_timeout = page_load_timeout

    def start_session(self, options: Options | None = None) -> WebDriver:
        """Start and return the first supported browser that Selenium can launch.

        Chrome-specific options are used only when starting Chrome. Edge and other browsers use their default options.
        """
        if self._driver is not None:
            return self._driver

        browsers = [
            ("Chrome", lambda: webdriver.Chrome(options=options)),
            ("Edge", webdriver.Edge),
        ]

        failures = []
        for name, start_browser in browsers:
            driver = None
            try:
                driver = start_browser()
                driver.set_page_load_timeout(self.page_load_timeout)
            except WebDriverException as error:
                if driver is not None:
                    try:
                        driver.quit()
                    except WebDriverException:
                        pass
                failures.append(f"{name}: {error}")
                continue

            self._driver = driver
            return driver

        raise RuntimeError(
            "Could not start any supported browser. " + "; ".join(failures)
        )

    def fetch(
        self,
        url: str,
        wait_for: tuple[str, str] | None = None,
        wait_timeout: float = 10.0,
    ) -> str:
        """Load a URL and return its rendered page source.

        If ``wait_for`` is provided, wait up to ``wait_timeout`` seconds for
        that Selenium locator, such as ``(By.CSS_SELECTOR, ".availability")``.
        Without a locator, return the page source after navigation completes.
        """
        driver = self.start_session()
        try:
            driver.get(url)
            if wait_for is not None:
                WebDriverWait(driver, wait_timeout).until(
                    EC.presence_of_element_located(wait_for)
                )
            return driver.page_source
        except WebDriverException as error:
            logger.warning("Browser fetch failed for %s: %s", url, error)
            raise

    def close(self) -> None:
        """Close the active browser, if one was started."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except WebDriverException:
                logger.debug("Failed to quit the browser cleanly", exc_info=True)
            finally:
                self._driver = None

    def __enter__(self) -> BrowserSession:
        """Return this session for use in a ``with`` statement."""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Close the browser when leaving a ``with`` statement."""
        self.close()

    