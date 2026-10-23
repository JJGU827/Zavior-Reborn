
import logging
from dataclasses import dataclass
from functions.metadata_normalizer import normalize_work

from functions.ao3_scraper import AO3ScraperError
from functions.ao3_selenium import (
    scrape_ao3_selenium,
    validate_ao3_url
)
from functions.fichub import scrape_fichub

logger = logging.getLogger("Zavior")


@dataclass
class RetrievalResult:
    work: object
    source: str
    normalized: object = None


async def retrieve_ao3_work(url):
    clean_url = validate_ao3_url(url)

    # STEP 1: Try FicHub first.
    logger.info(
        "Trying FicHub metadata: %s",
        clean_url
    )

    try:
        work = await scrape_fichub(clean_url)

        logger.info(
            "FicHub successfully retrieved: %s",
            work.title
        )

        return RetrievalResult(
            work=work,
            source="FicHub",
            normalized=normalize_work(work)
        )

    except AO3ScraperError as error:
        logger.warning(
            "FicHub failed: %s",
            error
        )

    # STEP 2: Fall back to Selenium.
    logger.info(
        "Falling back to headless AO3 scraper."
    )

    try:
        work = await scrape_ao3_selenium(
            clean_url,
            headless=True
        )

        logger.info(
            "Selenium successfully retrieved: %s",
            work.title
        )

        return RetrievalResult(
            work=work,
            source="AO3"
        )

    except AO3ScraperError as error:
        logger.warning(
            "AO3 scraper failed: %s",
            error
        )

        raise AO3ScraperError(
            "Unable to retrieve this work from "
            "either FicHub or AO3."
        ) from error
