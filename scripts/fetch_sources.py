"""
Fetch trending tech stories from free sources: RSS feeds, Hacker News, Reddit.
Outputs a list of normalized story dicts to stories_raw.json
"""
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
}

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

REDDIT_SUBS = ["technology", "programming"]


def fetch_url(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "linkedin-auto-poster/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def fetch_rss():
    stories = []
    for source, url in RSS_FEEDS.items():
        try:
            raw = fetch_url(url)
            root = ET.fromstring(raw)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                if title and link:
                    stories.append({
                        "title": title,
                        "url": link,
                        "source": source,
                        "fetched_at": int(time.time()),
                    })
        except Exception as e:
            print(f"[rss] failed for {source}: {e}")
    return stories


def fetch_hackernews(limit=25):
    stories = []
    try:
        ids = json.loads(fetch_url(HN_TOP_URL))[:limit]
        for story_id in ids:
            try:
                item = json.loads(fetch_url(HN_ITEM_URL.format(story_id)))
                if item.get("title") and item.get("url"):
                    stories.append({
                        "title": item["title"],
                        "url": item["url"],
                        "source": "Hacker News",
                        "score": item.get("score", 0),
                        "fetched_at": int(time.time()),
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"[hn] failed: {e}")
    return stories


def fetch_reddit():
    # Uses Reddit's public json endpoints (no auth needed for read-only, but
    # rate-limited more strictly without a registered app; swap in OAuth if
    # you hit limits — see REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET in README).
    stories = []
    for sub in REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=10"
        try:
            data = json.loads(fetch_url(url, headers={"User-Agent": "linkedin-auto-poster/1.0"}))
            for child in data["data"]["children"]:
                d = child["data"]
                stories.append({
                    "title": d["title"],
                    "url": d.get("url_overridden_by_dest") or f"https://reddit.com{d['permalink']}",
                    "source": f"Reddit r/{sub}",
                    "score": d.get("score", 0),
                    "fetched_at": int(time.time()),
                })
        except Exception as e:
            print(f"[reddit] failed for r/{sub}: {e}")
    return stories


def main():
    all_stories = fetch_rss() + fetch_hackernews() + fetch_reddit()
    os.makedirs("data", exist_ok=True)
    with open("data/stories_raw.json", "w") as f:
        json.dump(all_stories, f, indent=2)
    print(f"Fetched {len(all_stories)} stories")


if __name__ == "__main__":
    main()
