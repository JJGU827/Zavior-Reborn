
import asyncio
import atexit
import logging
import re
import threading
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from functions.ao3_scraper import (
    AO3ScraperError,
    parse_ao3_html,
)


logger = logging.getLogger("Zavior")

REQUEST_INTERVAL = 5

_driver = None
_driver_headless = None
_last_request = 0.0

_browser_lock = threading.Lock()





def validate_ao3_url(url):
    url = str(url).strip()

    # Support Markdown-formatted links.
    markdown_match = re.fullmatch(
        r"\[[^\]]+\]\((https?://[^)\s]+)\)",
        url
    )

    if markdown_match:
        url = markdown_match.group(1)

    # Remove Discord angle brackets.
    url = url.strip("<>")

    parsed = urlparse(url)

    # Accept both HTTP and HTTPS input.
    if parsed.scheme not in ("http", "https"):
        raise AO3ScraperError(
            "Invalid AO3 URL: unsupported scheme."
        )

    if parsed.hostname not in (
        "archiveofourown.org",
        "www.archiveofourown.org"
    ):
        raise AO3ScraperError(
            "Invalid AO3 URL: unrecognized hostname."
        )

    if parsed.port is not None:
        raise AO3ScraperError(
            "Invalid AO3 URL: custom ports are not supported."
        )

    # Accept both work URLs and chapter URLs.
    match = re.fullmatch(
        r"/works/(\d+)(?:/chapters/\d+)?/?",
        parsed.path
    )

    if not match:
        raise AO3ScraperError(
            "Invalid AO3 URL: unrecognized work path."
        )

    work_id = match.group(1)

    # Always return the canonical HTTPS work URL.
    clean_url = (
        "https://archiveofourown.org/works/"
        + work_id
    )

    logger.info(
        "Validated AO3 URL: %s",
        clean_url
    )

    return clean_url

    url = str(url).strip()

    logger.info("Validating AO3 URL: %r", url)

    # Support Markdown-formatted links.
    markdown_match = re.fullmatch(
        r"\[[^\]]+\]\((https?://[^)\s]+)\)",
        url
    )

    if markdown_match:
        url = markdown_match.group(1)

    # Remove Discord angle brackets.
    url = url.strip("<>")

    logger.warning("RAW URL: %r", url)
    logger.warning("URL CHARACTER CODES: %s", [ord(c) for c in url])
    parsed = urlparse(url)

    logger.warning("PARSED SCHEME: %r", parsed.scheme)
    logger.warning("PARSED HOSTNAME: %r", parsed.hostname)
    logger.warning("PARSED PATH: %r", parsed.path)

    logger.info(
        "Parsed URL: scheme=%r, hostname=%r, path=%r",
        parsed.scheme,
        parsed.hostname,
        parsed.path
    )

    if parsed.scheme != "https":
        raise AO3ScraperError(
            "Invalid AO3 URL: HTTPS is required."
        )

    if parsed.hostname not in (
        "archiveofourown.org",
        "www.archiveofourown.org"
    ):
        raise AO3ScraperError(
            "Invalid AO3 URL: unrecognized hostname."
        )

    if parsed.port is not None:
        raise AO3ScraperError(
            "Invalid AO3 URL: custom ports are not supported."
        )

    match = re.fullmatch(
        r"/works/(\d+)(?:/chapters/\d+)?/?",
        parsed.path
    )

    if not match:
        raise AO3ScraperError(
            "Invalid AO3 URL: unrecognized work path."
        )

    work_id = match.group(1)

    clean_url = (
        "https://archiveofourown.org/works/"
        + work_id
    )

    logger.info("Validated AO3 URL: %s", clean_url)

    return clean_url

from pathlib import Path

def create_driver(headless=False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1280,900")
    options.page_load_strategy = "eager"

    profile_directory = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "chrome_profile"
    )

    profile_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    options.add_argument(
        "--user-data-dir=" + str(profile_directory)
    )

    logger.info("Starting Selenium Chrome browser...")

    service = Service(
        ChromeDriverManager().install()
    )

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    driver.set_page_load_timeout(25)

    logger.info("Chrome launched successfully.")

    return driver


def close_driver():
    global _driver
    global _driver_headless

    if _driver is not None:
        try:
            logger.info("Closing Selenium Chrome browser.")
            _driver.quit()
        except Exception:
            logger.exception(
                "Error while closing Chrome."
            )

    _driver = None
    _driver_headless = None


def get_driver(headless=False):
    global _driver
    global _driver_headless

    if _driver is not None:
        try:
            _driver.current_window_handle

            if _driver_headless == headless:
                return _driver

        except WebDriverException:
            logger.warning(
                "Existing Chrome session is unavailable."
            )

        close_driver()

    _driver = create_driver(headless=headless)
    _driver_headless = headless

    return _driver


def check_ao3_page(driver):
    title = driver.title.lower()

    if (
        "525" in title
        and "ssl handshake failed" in title
    ):
        raise AO3ScraperError(
            "AO3 returned Cloudflare error 525. "
            "Please try again later."
        )

    if (
        "just a moment" in title
        or "attention required" in title
        or "verify you are human" in title
    ):
        raise AO3ScraperError(
            "AO3 is requesting human verification. "
            "Automatic retrieval is unavailable."
        )

    parsed = urlparse(driver.current_url)

    if parsed.hostname not in (
        "archiveofourown.org",
        "www.archiveofourown.org",
    ):
        raise AO3ScraperError(
            "The browser was redirected away from AO3."
        )


def scrape_ao3_selenium_sync(url, headless=False):
    global _last_request

    clean_url = validate_ao3_url(url)

    with _browser_lock:
        driver = get_driver(headless=headless)

        elapsed = time.monotonic() - _last_request

        if _last_request and elapsed < REQUEST_INTERVAL:
            delay = REQUEST_INTERVAL - elapsed

            logger.info(
                "Waiting %.1f seconds before AO3 request.",
                delay
            )

            time.sleep(delay)

        logger.info("Navigating to AO3: %s", clean_url)

        _last_request = time.monotonic()

        try:
            driver.get(clean_url + "?view_adult=true")

        except TimeoutException as error:
            logger.error(
                "AO3 navigation timed out. "
                "Current URL: %s",
                driver.current_url
            )

            raise AO3ScraperError(
                "Chrome timed out while navigating to AO3."
            ) from error

        except WebDriverException as error:
            logger.exception("Chrome navigation failed.")

            raise AO3ScraperError(
                "Chrome could not navigate to AO3."
            ) from error

        logger.info(
            "Current URL: %s",
            driver.current_url
        )

        logger.info(
            "Page title: %s",
            driver.title
        )

        check_ao3_page(driver)

        try:
            WebDriverWait(driver, 15).until(
                lambda browser: (
                    len(
                        browser.find_elements(
                            By.CSS_SELECTOR,
                            "dl.work.meta.group"
                        )
                    ) > 0
                    or "525" in browser.title.lower()
                    or "just a moment" in browser.title.lower()
                )
            )

        except TimeoutException as error:
            logger.error(
                "Metadata was not found. "
                "Page title: %s",
                driver.title
            )

            raise AO3ScraperError(
                "AO3 loaded, but the work metadata "
                "was not found."
            ) from error

        check_ao3_page(driver)

        html = driver.page_source

        soup = BeautifulSoup(html, "lxml")

        if soup.select_one("dl.work.meta.group") is None:
            raise AO3ScraperError(
                "AO3 did not return a readable work page."
            )

        work = parse_ao3_html(
            html,
            clean_url
        )

        logger.info(
            "Successfully retrieved AO3 work: %s",
            work.title
        )

        logger.info(
            "Found %s relationships, %s characters, "
            "and %s additional tags.",
            len(work.relationships),
            len(work.characters),
            len(work.additional_tags)
        )

        return work


async def scrape_ao3_selenium(url, headless=False):
    return await asyncio.to_thread(
        scrape_ao3_selenium_sync,
        url,
        headless
    )


atexit.register(close_driver)
