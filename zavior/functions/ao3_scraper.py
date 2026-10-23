import asyncio
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


logger = logging.getLogger("Zavior")


class AO3ScraperError(Exception):
    pass


@dataclass
class AO3Work:
    url: str
    title: str = "Unknown"
    authors: list = field(default_factory=list)
    fandoms: list = field(default_factory=list)
    rating: str = "Unknown"
    warnings: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    characters: list = field(default_factory=list)
    additional_tags: list = field(default_factory=list)
    language: str = "Unknown"
    words: str = "Unknown"
    chapters: str = "Unknown"
    kudos: str = "Unknown"
    bookmarks: str = "Unknown"
    hits: str = "Unknown"
    published: str = "Unknown"
    updated: str = "Unknown"
    completed: str = "Unknown"
    summary: str = "No summary provided."
    status: str = "Unknown"



def get_tag_list(soup, class_name):
    """
    Extract AO3 tags from the work metadata.

    Examples:
        fandom
        warning
        category
        relationship
        character
        freeform
    """

    selectors = [
        "dl.work.meta.group dd." + class_name + ".tags a.tag",
        "dd." + class_name + ".tags a.tag",
        "dd." + class_name + " a.tag",
    ]

    for selector in selectors:
        elements = soup.select(selector)

        if elements:
            tags = [
                element.get_text(" ", strip=True)
                for element in elements
            ]

            return list(dict.fromkeys(tags))

    return []


def get_stat(soup, class_name):
    element = soup.select_one(
        "dl.stats dd." + class_name
    )

    if element is None:
        return "Unknown"

    return element.get_text(" ", strip=True)


def get_meta_value(soup, class_name):
    element = soup.select_one(
        "dl.work.meta.group dd." + class_name
    )

    if element is None:
        return "Unknown"

    return element.get_text(" ", strip=True)


def parse_ao3_html(html, url):
    soup = BeautifulSoup(html, "html.parser")

    metadata = soup.select_one("dl.work.meta.group")
    heading = soup.select_one("h2.title.heading")

    if metadata is None or heading is None:
        raise AO3ScraperError(
            "AO3 did not return a readable story page. "
            "It may be restricted or blocked by Cloudflare."
        )

    work = AO3Work(url=url)

    work.title = heading.get_text(" ", strip=True)

    author_links = soup.select(
        "h3.byline.heading a[rel='author']"
    )

    work.authors = [
        author.get_text(" ", strip=True)
        for author in author_links
    ] or ["Anonymous"]

    work.fandoms = get_tag_list(soup, "fandom")
    work.warnings = get_tag_list(soup, "warning")
    work.categories = get_tag_list(soup, "category")
    work.relationships = get_tag_list(soup, "relationship")
    work.characters = get_tag_list(soup, "character")
    work.additional_tags = get_tag_list(soup, "freeform")

    work.rating = get_meta_value(soup, "rating")

    work.language = get_stat(soup, "language")
    work.words = get_stat(soup, "words")
    work.chapters = get_stat(soup, "chapters")
    work.kudos = get_stat(soup, "kudos")
    work.bookmarks = get_stat(soup, "bookmarks")
    work.hits = get_stat(soup, "hits")
    work.published = get_stat(soup, "published")

    status_element = soup.select_one("dl.stats dt.status")
    status_date = get_stat(soup, "status")

    if status_element:
        label = status_element.get_text(" ", strip=True)

        if "Completed" in label:
            work.completed = status_date
        else:
            work.updated = status_date

    summary_element = soup.select_one(
        "div.summary.module blockquote.userstuff"
    )

    if summary_element:
        work.summary = summary_element.get_text(
            "\n", strip=True
        )

    match = re.fullmatch(r"(\d+)/(\d+|\?)", work.chapters)

    if match:
        current, total = match.groups()

        if total != "?" and current == total:
            work.status = "Complete"
        else:
            work.status = "In Progress"

    return work


async def scrape_ao3(url):
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "archiveofourown.org"
        or not re.fullmatch(r"/works/\d+", parsed.path)
        or parsed.port is not None
    ):
        raise AO3ScraperError("Invalid AO3 work URL.")

    logger.info("Opening AO3 work: %s", url)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=False
            )

            try:
                context = await browser.new_context(
                    locale="en-US"
                )

                page = await context.new_page()

                response = await page.goto(
                    url + "?view_adult=true",
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                if response is None:
                    raise AO3ScraperError(
                        "AO3 did not return a response."
                    )

                if response.status == 429:
                    raise AO3ScraperError(
                        "AO3 is rate-limiting requests."
                    )

                if response.status in (401, 403):
                    raise AO3ScraperError(
                        "AO3 denied access to this request."
                    )

                if response.status == 404:
                    raise AO3ScraperError(
                        "AO3 work not found."
                    )

                if response.status >= 400:
                    raise AO3ScraperError(
                        "AO3 returned HTTP "
                        + str(response.status)
                    )

                # Check that we stayed on AO3
                final_url = urlparse(page.url)

                if final_url.hostname != "archiveofourown.org":
                    raise AO3ScraperError(
                        "AO3 redirected to an unexpected website."
                    )

                # Allow the work metadata to appear
                try:
                    await page.locator(
                        "dl.work.meta.group"
                    ).wait_for(timeout=10000)

                except PlaywrightTimeoutError:
                    page_title = await page.title()

                    logger.warning(
                        "AO3 metadata not found. Page title: %s",
                        page_title
                    )

                    raise AO3ScraperError(
                        "AO3 metadata was not available. "
                        "The page may be restricted or "
                        "showing a Cloudflare challenge."
                    )

                html = await page.content()

                return parse_ao3_html(html, url)

            finally:
                await browser.close()

    except PlaywrightTimeoutError as error:
        raise AO3ScraperError(
            "Timed out while loading AO3."
        ) from error

    except AO3ScraperError:
        raise

    except Exception as error:
        logger.exception("Playwright AO3 scraping failed")

        raise AO3ScraperError(
            "Unable to retrieve AO3 metadata."
        ) from error
