
import json
import urllib.error
import urllib.parse
import urllib.request

AO3_URL = "https://archiveofourown.org/works/26200348"

API_URL = "https://fichub.net/api/v0/meta"

params = urllib.parse.urlencode({
    "q": AO3_URL
})

request = urllib.request.Request(
    API_URL + "?" + params,
    headers={
        "User-Agent": "Zavior/0.1 (personal AO3 metadata testing; contact: your-email@example.com)",
        "Accept": "application/json"
    }
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)

    print(json.dumps(data, indent=2, ensure_ascii=False))

except urllib.error.HTTPError as error:
    print("HTTP error:", error.code)

    if error.code == 429:
        print("Retry-After:", error.headers.get("Retry-After"))

except urllib.error.URLError as error:
    print("Connection error:", error.reason)

except json.JSONDecodeError:
    print("The API did not return valid JSON.")
