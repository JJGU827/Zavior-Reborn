import re
from urllib.parse import urlparse


def parse_fanfiction_url(url):
    url = url.strip().strip("<>")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    domain = (parsed.hostname or "").lower()

    if domain.startswith("www."):
        domain = domain[4:]

    path = parsed.path.rstrip("/")

    # Archive of Our Own
    if domain == "archiveofourown.org":
        match = re.fullmatch(
            r"/works/(\d+)(?:/chapters/\d+)?",
            path
        )

        if match:
            story_id = match.group(1)

            return {
                "site": "Archive of Our Own (AO3)",
                "story_id": story_id,
                "url": (
                    "https://archiveofourown.org/works/"
                    + story_id
                )
            }

    # FanFiction.net
    elif domain in ("fanfiction.net", "m.fanfiction.net"):
        match = re.fullmatch(
            r"/s/(\d+)(?:/\d+(?:/[^/]*)?)?",
            path
        )

        if match:
            story_id = match.group(1)

            return {
                "site": "FanFiction.net (FFN)",
                "story_id": story_id,
                "url": (
                    "https://www.fanfiction.net/s/"
                    + story_id
                    + "/1/"
                )
            }

    return None
