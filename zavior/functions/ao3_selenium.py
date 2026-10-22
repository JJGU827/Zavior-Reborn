
import asyncio
import logging
import re
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from functions.ao3_scraper import (
    AO3ScraperError,
    parse_ao3_html,
)

logger = logging.getLogger("Zavior")


def scrape_ao3_selenium_sync(url, headless=False):
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "archiveofourown.org"
        or not re.fullmatch(r"/works/\d+", parsed.path)
        or parsed.port is not None
    ):
        raise AO3ScraperError("Invalid AO3 work URL.")

    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1280,900")

    driver = None

    try:
        service = Service(
            ChromeDriverManager().install()
        )

        driver = webdriver.Chrome(
            service=service,
            options=options,
        )

        driver.set_page_load_timeout(30)

        logger.info("Opening AO3 with Selenium: %s", url)

        driver.get(url + "?view_adult=true")

        # Wait for the AO3 metadata section.
        # If verification appears, this will eventually time out.
        WebDriverWait(driver, 15).until(
            lambda browser: (
                len(
                    browser.find_elements(
                        "css selector",
                        "dl.work.meta.group"
                    )
                ) > 0
                or "just a moment" in browser.title.lower()
            )
        )

        page_title = driver.title
        html = driver.page_source

        logger.info("AO3 page title: %s", page_title)

        if "just a moment" in page_title.lower():
            raise AO3ScraperError(
                "AO3 presented a Cloudflare verification "
                "challenge. Automatic retrieval is unavailable."
            )

        if not driver.find_elements(
            "css selector",
            "dl.work.meta.group"
        ):
            raise AO3ScraperError(
                "AO3 did not return work metadata."
            )

        return parse_ao3_html(html, url)

    except TimeoutException as error:
        raise AO3ScraperError(
            "Timed out waiting for AO3 metadata. "
            "The work may be unavailable, restricted, "
            "or showing a verification challenge."
        ) from error

    except WebDriverException as error:
        logger.warning("Selenium browser error: %s", error)

        raise AO3ScraperError(
            "Chrome could not retrieve the AO3 page."
        ) from error

    finally:
        if driver is not None:
            driver.quit()


async def scrape_ao3_selenium(url, headless=False):
    # Selenium is synchronous.
    # Run it in a worker thread so Discord stays responsive.
    return await asyncio.to_thread(
        scrape_ao3_selenium_sync,
        url,
        headless,
    )
