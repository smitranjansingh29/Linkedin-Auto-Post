"""
Dedupe near-identical stories and score the rest by trend strength.
Reads data/stories_raw.json, writes data/top_story.json (the single best pick).
"""
import json
import re
from difflib import SequenceMatcher

KEYWORDS = [
    "ai", "llm", "gpt", "model", "chip", "startup", "funding", "open source",
    "cloud", "security", "breach", "robot", "quantum", "developer", "api",
]

SIMILARITY_THRESHOLD = 0.6


def normalize(title):
    return re.sub(r"[^a-z0-9 ]", "", title.lower())


def is_duplicate(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio() > SIMILARITY_THRESHOLD


def dedupe(stories):
    kept = []
    for story in stories:
        if not any(is_duplicate(story["title"], k["title"]) for k in kept):
            kept.append(story)
        else:
            # story is a duplicate of one we're keeping -> counts as extra
            # source coverage, which we treat as a trend signal
            for k in kept:
                if is_duplicate(story["title"], k["title"]):
                    k["source_count"] = k.get("source_count", 1) + 1
                    break
    return kept


def score(story):
    s = 0
    s += story.get("source_count", 1) * 10  # covered by multiple sources = trending
    s += min(story.get("score", 0), 500) / 10  # HN/Reddit upvotes, capped
    title_lower = story["title"].lower()
    s += sum(3 for kw in KEYWORDS if kw in title_lower)
    return s


def main():
    with open("data/stories_raw.json") as f:
        stories = json.load(f)

    if not stories:
        print("No stories fetched, nothing to score")
        return

    deduped = dedupe(stories)
    for story in deduped:
        story["trend_score"] = score(story)

    deduped.sort(key=lambda s: s["trend_score"], reverse=True)

    with open("data/top_story.json", "w") as f:
        json.dump(deduped[0], f, indent=2)

    print(f"Deduped to {len(deduped)} stories. Top pick: {deduped[0]['title']}")


if __name__ == "__main__":
    main()
