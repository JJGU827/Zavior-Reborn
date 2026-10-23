
import asyncio
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from functions.ao3_scraper import AO3Work, AO3ScraperError

logger = logging.getLogger("Zavior")

FICHUB_API = "https://fichub.net/api/v0/meta"

# Set FICHUB_CONTACT in .env to a real contact address.
FICHUB_CONTACT = os.getenv("FICHUB_CONTACT", "")

_api_lock = asyncio.Lock()


def first_value(data, *keys, default=None):
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return default


def as_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                name = first_value(
                    item, "name", "tag", "value"
                )
                if name is not None:
                    result.append(str(name))
        return result

    if isinstance(value, str):
        return [value] if value else []

    return []


def as_text(value):
    if value is None:
        return ""

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        return value

    return ""



def normalize_fichub_metadata(payload, url):
    from bs4 import BeautifulSoup

    if not isinstance(payload, dict):
        raise AO3ScraperError(
            "FicHub returned an unexpected response."
        )

    if payload.get("err") not in (None, 0, "0"):
        raise AO3ScraperError(
            "FicHub could not retrieve this work."
        )

    metadata = payload.get("meta", payload)

    if not isinstance(metadata, dict):
        raise AO3ScraperError(
            "FicHub returned invalid metadata."
        )

    title = metadata.get("title")

    if not title:
        raise AO3ScraperError(
            "FicHub returned no work title."
        )

    extended = metadata.get("rawExtendedMeta") or {}
    stats = extended.get("stats") or {}

    if not isinstance(extended, dict):
        extended = {}

    if not isinstance(stats, dict):
        stats = {}

    def get_tags(key):
        value = extended.get(key, [])

        if isinstance(value, list):
            return [
                str(item)
                for item in value
                if item is not None
            ]

        if isinstance(value, str):
            return [value] if value else []

        return []

    def get_stat(key, fallback=""):
        value = stats.get(key)

        if value is None:
            value = metadata.get(key, fallback)

        return str(value) if value is not None else ""

    author = metadata.get("author", "")

    if isinstance(author, str):
        authors = [author] if author else []
    elif isinstance(author, list):
        authors = [
            str(item)
            for item in author
            if item
        ]
    else:
        authors = []

    description_html = metadata.get(
        "description", ""
    )

    if isinstance(description_html, str):
        summary = BeautifulSoup(
            description_html,
            "html.parser"
        ).get_text(
            separator="\n",
            strip=True
        )
    else:
        summary = ""

    rating_tags = get_tags("rating")

    rating = (
        rating_tags[0]
        if rating_tags
        else ""
    )

    status_value = str(
        metadata.get("status", "")
    ).lower()

    if status_value == "complete":
        status = "Complete"
    elif status_value in ("ongoing", "in-progress"):
        status = "In Progress"
    else:
        status = status_value.title()

    chapters = get_stat("chapters")

    # FicHub provides full chapter counts in
    # rawExtendedMeta.stats.chapters, e.g. "69/69".
    # Prefer that over the top-level integer.
    published = get_stat("published")

    updated = metadata.get("updated", "")

    if isinstance(updated, str) and "T" in updated:
        updated = updated.split("T", 1)[0]

    completed = ""

    if status == "Complete":
        completed = updated

    return AO3Work(
        url=url,
        title=str(title),
        authors=authors,
        fandoms=get_tags("fandom"),
        rating=rating,
        warnings=get_tags("warning"),
        categories=get_tags("category"),
        relationships=get_tags("relationship"),
        characters=get_tags("character"),
        additional_tags=get_tags("freeform"),
        language=str(
            extended.get("language")
            or metadata.get("language")
            or ""
        ),
        words=get_stat("words"),
        chapters=chapters,
        kudos=get_stat("kudos"),
        bookmarks=get_stat("bookmarks"),
        hits=get_stat("hits"),
        published=published,
        updated=str(updated),
        completed=completed,
        summary=summary,
        status=status
    )

    if not isinstance(payload, dict):
        raise AO3ScraperError(
            "FicHub returned an unexpected response."
        )

    if payload.get("err") not in (None, 0, "0"):
        raise AO3ScraperError(
            "FicHub could not retrieve this work."
        )

    metadata = payload.get("meta", payload)

    if not isinstance(metadata, dict):
        raise AO3ScraperError(
            "FicHub returned invalid metadata."
        )

    title = first_value(
        metadata, "title", "name"
    )

    if not title:
        raise AO3ScraperError(
            "FicHub returned no work title."
        )

    author = first_value(
        metadata, "author", "authors", default=[]
    )

    if isinstance(author, dict):
        author = first_value(
            author, "name", "username", default=""
        )

    authors = as_list(author)

    # FicHub's API does not guarantee AO3-specific
    # relationship, character, and freeform tag fields.
    return AO3Work(
        url=url,
        title=as_text(title),
        authors=authors,
        fandoms=as_list(
            first_value(
                metadata, "fandoms", "fandom"
            )
        ),
        rating=as_text(
            first_value(metadata, "rating")
        ),
        warnings=as_list(
            first_value(
                metadata, "warnings", "warning"
            )
        ),
        categories=as_list(
            first_value(
                metadata, "categories", "category"
            )
        ),
        relationships=as_list(
            first_value(
                metadata, "relationships", "ships"
            )
        ),
        characters=as_list(
            first_value(metadata, "characters")
        ),
        additional_tags=as_list(
            first_value(
                metadata,
                "additional_tags",
                "additionalTags",
                "freeform_tags"
            )
        ),
        language=as_text(
            first_value(metadata, "language")
        ),
        words=as_text(
            first_value(
                metadata, "words", "wordCount",
                "word_count"
            )
        ),
        chapters=as_text(
            first_value(
                metadata, "chapters", "chapterCount",
                "chapter_count"
            )
        ),
        kudos=as_text(
            first_value(metadata, "kudos")
        ),
        bookmarks=as_text(
            first_value(metadata, "bookmarks")
        ),
        hits=as_text(
            first_value(metadata, "hits")
        ),
        published=as_text(
            first_value(
                metadata, "published", "publishedDate"
            )
        ),
        updated=as_text(
            first_value(
                metadata, "updated", "updatedDate"
            )
        ),
        completed=as_text(
            first_value(
                metadata, "completed", "completedDate"
            )
        ),
        summary=as_text(
            first_value(
                metadata, "summary", "description"
            )
        ),
        status=as_text(
            first_value(metadata, "status")
        )
    )


def fetch_fichub_sync(url):
    if not FICHUB_CONTACT:
        raise AO3ScraperError(
            "FICHUB_CONTACT is not configured."
        )

    query = urllib.parse.urlencode({"q": url})

    request = urllib.request.Request(
        FICHUB_API + "?" + query,
        headers={
            "User-Agent": (
                "Zavior/0.1 +" + FICHUB_CONTACT
            ),
            "Accept": "application/json"
        }
    )

    logger.info("Requesting FicHub metadata: %s", url)

    try:
        with urllib.request.urlopen(
            request,
            timeout=25
        ) as response:
            payload = json.load(response)

    except urllib.error.HTTPError as error:
        if error.code == 429:
            logger.warning(
                "FicHub rate limited the request. "
                "Retry-After: %s",
                error.headers.get("Retry-After")
            )
            raise AO3ScraperError(
                "FicHub is rate limiting requests."
            ) from error

        raise AO3ScraperError(
            "FicHub returned HTTP " + str(error.code)
        ) from error

    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError
    ) as error:
        raise AO3ScraperError(
            "Could not retrieve FicHub metadata."
        ) from error

    return normalize_fichub_metadata(payload, url)


async def scrape_fichub(url):
    async with _api_lock:
        return await asyncio.to_thread(
            fetch_fichub_sync, url
        )
