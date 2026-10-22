
from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://archiveofourown.org/works/26200348"

try:
    response = requests.get(
        url,
        timeout=20
    )

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title = soup.select_one("h2.title.heading")
    metadata = soup.select_one("dl.work.meta.group")

    if title and metadata:
        print("AO3 work page retrieved.")
        print("Title:", title.get_text(" ", strip=True))
    else:
        print("AO3 metadata was not available.")
        print("Page title:", soup.title.get_text(strip=True) if soup.title else "Unknown")

except requests.RequestsError as error:
    print("Request failed:", error)
