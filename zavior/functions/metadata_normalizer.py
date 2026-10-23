
import re
from dataclasses import dataclass, field


FANDOM_RULES = {
    "percy_jackson": {
        "name": "Percy Jackson / Riordanverse",
        "umbrella_tags": [
            "Percy Jackson and the Olympians & Related Fandoms - All Media Types"
        ],
        "series": {
            "Percy Jackson and the Olympians - Rick Riordan":
                "Percy Jackson and the Olympians",
            "The Heroes of Olympus - Rick Riordan":
                "The Heroes of Olympus",
            "The Trials of Apollo - Rick Riordan":
                "The Trials of Apollo",
            "Magnus Chase and the Gods of Asgard - Rick Riordan":
                "Magnus Chase and the Gods of Asgard",
            "The Kane Chronicles - Rick Riordan":
                "The Kane Chronicles",
        }
    }
}


TAG_ALIASES = {
    "percy jackson needs a hug": "Hurt Percy Jackson",
    "hurt percy jackson": "Hurt Percy Jackson",
    "powerful percy jackson": "Powerful Percy Jackson",
    "bamf percy jackson": "BAMF Percy Jackson",
    "hurt/comfort": "Hurt/Comfort",
    "canon divergence": "Canon Divergence",
    "dark percy jackson": "Dark Percy Jackson",
    "angst with a happy ending": "Angst with a Happy Ending",
}


@dataclass
class NormalizedMetadata:
    franchises: list = field(default_factory=list)
    series: list = field(default_factory=list)
    other_fandoms: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    themes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def unique_tags(tags):
    result = []
    seen = set()

    for tag in tags:
        if not isinstance(tag, str):
            continue

        tag = tag.strip()
        key = tag.casefold()

        if tag and key not in seen:
            result.append(tag)
            seen.add(key)

    return result


def normalize_fandoms(fandoms):
    franchises = []
    series = []
    other_fandoms = []

    matched = set()

    for rule in FANDOM_RULES.values():
        umbrella = set(rule["umbrella_tags"])
        series_map = rule["series"]

        relevant = [
            tag for tag in fandoms
            if tag in umbrella or tag in series_map
        ]

        if not relevant:
            continue

        franchises.append(rule["name"])
        matched.update(relevant)

        for tag in relevant:
            if tag in series_map:
                series.append(series_map[tag])

    for tag in fandoms:
        if tag not in matched:
            other_fandoms.append(tag)

    return (
        unique_tags(franchises),
        unique_tags(series),
        unique_tags(other_fandoms)
    )


def normalize_themes(tags):
    result = []

    for tag in tags:
        key = re.sub(r"\s+", " ", tag.strip()).casefold()

        if key in TAG_ALIASES:
            result.append(TAG_ALIASES[key])

    return unique_tags(result)


def normalize_work(work):
    franchises, series, other = normalize_fandoms(
        work.fandoms
    )

    return NormalizedMetadata(
        franchises=franchises,
        series=series,
        other_fandoms=other,
        relationships=unique_tags(work.relationships),
        themes=normalize_themes(work.additional_tags),
        warnings=unique_tags(work.warnings)
    )
