
import asyncio

from functions.ao3_selenium import scrape_ao3_selenium
from functions.ao3_scraper import AO3ScraperError


def print_tags(label, tags):
    print("\n" + label + ":")

    if not tags:
        print("  None found")
        return

    for tag in tags:
        print("  - " + tag)


async def main():
    url = input("Enter an AO3 work URL: ").strip()

    try:
        work = await scrape_ao3_selenium(
            url,
            headless=False,
        )

        print("\n========== AO3 WORK ==========")

        print("Title:", work.title)
        print("Authors:", ", ".join(work.authors))
        print("Rating:", work.rating)

        print_tags("Fandoms", work.fandoms)
        print_tags("Warnings", work.warnings)
        print_tags("Categories", work.categories)
        print_tags("Relationships", work.relationships)
        print_tags("Characters", work.characters)
        print_tags("Additional Tags", work.additional_tags)

        print("\n========== STATISTICS ==========")

        print("Words:", work.words)
        print("Chapters:", work.chapters)
        print("Status:", work.status)
        print("Kudos:", work.kudos)
        print("Bookmarks:", work.bookmarks)
        print("Hits:", work.hits)

        print("\n========== SUMMARY ==========")
        print(work.summary)

    except AO3ScraperError as error:
        print("\nScraping failed:", error)


if __name__ == "__main__":
    asyncio.run(main())
