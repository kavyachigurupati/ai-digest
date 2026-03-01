# scraper.py
# -------------------------------------------------------------------------
# PURPOSE: Fetch articles from RSS feeds and Hacker News API.
#          Saves results to raw_articles.json for analyzer.py to process.
#
# FLOW:
#   1. Load sources from sources.json
#   2. For each RSS source: fetch feed, parse entries, extract title/url/description
#   3. For Hacker News: hit the public API, filter by min score, get top stories
#   4. Deduplicate by URL against existing digest.json (skip already-seen articles)
#   5. Save all new raw articles to raw_articles.json
#
# RUN:
#   poetry run python scraper.py
# -------------------------------------------------------------------------

import json
import os
import ssl
import time
from datetime import datetime, timezone
ssl._create_default_https_context = ssl._create_unverified_context
import feedparser  # parses RSS/Atom feeds
import requests    # for Hacker News API calls

# ── Config ────────────────────────────────────────────────────────────────

# Path to the sources config file
SOURCES_FILE = "sources.json"

# Output file: raw articles for analyzer.py to read
RAW_OUTPUT_FILE = "raw_articles.json"

# Existing digest: used to skip already-summarized URLs
DIGEST_FILE = "digest.json"

# Max articles to pull per RSS source (keeps token count manageable for Claude)
MAX_PER_SOURCE = 5

# Max HN stories to fetch (we filter by score, so cast a wide net)
HN_TOP_STORIES_LIMIT = 50


# ── Helpers ───────────────────────────────────────────────────────────────

def load_existing_urls() -> set:
    """
    Load URLs already in digest.json so we can skip duplicates.
    Returns an empty set if digest.json doesn't exist yet.
    """
    if not os.path.exists(DIGEST_FILE):
        return set()

    with open(DIGEST_FILE, "r") as f:
        existing = json.load(f)

    # Build a set of URLs for fast O(1) lookup
    return {entry["url"] for entry in existing}


def parse_rss_source(source: dict, seen_urls: set) -> list:
    """
    Fetch and parse a single RSS/Atom feed.

    Args:
        source: dict from sources.json with keys: name, url, category
        seen_urls: set of URLs already in digest.json

    Returns:
        List of raw article dicts (title, url, description, source, category)
    """
    print(f"  Fetching RSS: {source['name']} ...")
    articles = []

    try:
        # feedparser handles RSS 1.0, RSS 2.0, and Atom formats automatically
        feed = feedparser.parse(source["url"])

        # feedparser doesn't raise exceptions — check bozo flag for parse errors
        if feed.bozo:
            print(f"    [WARN] Feed parse issue for {source['name']}: {feed.bozo_exception}")

        for entry in feed.entries[:MAX_PER_SOURCE]:
            url = entry.get("link", "")

            # Skip if we've already summarized this URL
            if not url or url in seen_urls:
                continue

            # Extract description: try 'summary' first, then 'description'
            description = entry.get("summary", entry.get("description", ""))

            # Strip HTML tags from description if present (basic cleanup)
            # feedparser sometimes includes raw HTML in summaries
            description = _strip_html(description)

            articles.append({
                "title": entry.get("title", "No title"),
                "url": url,
                "description": description[:500],  # cap at 500 chars to save tokens
                "source": source["name"],
                "category": source["category"],
                "scraped_at": datetime.now(timezone.utc).isoformat()
            })

    except Exception as e:
        # Don't crash the whole scraper if one source fails
        print(f"    [ERROR] Failed to fetch {source['name']}: {e}")

    print(f"    Found {len(articles)} new articles")
    return articles


def fetch_hacker_news(source: dict, seen_urls: set) -> list:
    """
    Fetch top Hacker News stories via the public Firebase API.
    Only includes stories with score >= min_score from sources.json.

    Args:
        source: dict from sources.json with keys: url, min_score, category
        seen_urls: set of URLs already in digest.json

    Returns:
        List of raw article dicts
    """
    print(f"  Fetching Hacker News (min score: {source['min_score']}) ...")
    articles = []
    base_url = source["url"]
    min_score = source.get("min_score", 200)

    try:
        # Step 1: Get list of top story IDs
        top_stories_url = f"{base_url}/topstories.json"
        response = requests.get(top_stories_url, timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:HN_TOP_STORIES_LIMIT]  # only check top N

        # Step 2: Fetch each story's details and filter by score
        for story_id in story_ids:
            story_url = f"{base_url}/item/{story_id}.json"
            story_resp = requests.get(story_url, timeout=10)
            story_resp.raise_for_status()
            story = story_resp.json()

            # Skip if missing required fields
            if not story or story.get("type") != "story":
                continue

            url = story.get("url", "")
            score = story.get("score", 0)

            # Filter: must have a URL, meet min score, and not already seen
            if not url or score < min_score or url in seen_urls:
                continue

            articles.append({
                "title": story.get("title", "No title"),
                "url": url,
                "description": f"Hacker News score: {score}. {story.get('text', '')[:300]}",
                "source": "Hacker News",
                "category": source["category"],
                "scraped_at": datetime.now(timezone.utc).isoformat()
            })

            # Small delay to be polite to the HN API
            time.sleep(0.1)

            # Cap at MAX_PER_SOURCE results
            if len(articles) >= MAX_PER_SOURCE:
                break

    except Exception as e:
        print(f"    [ERROR] Failed to fetch Hacker News: {e}")

    print(f"    Found {len(articles)} new HN articles above score threshold")
    return articles


def _strip_html(text: str) -> str:
    """
    Basic HTML tag stripping. Removes <tag> patterns from text.
    Not a full HTML parser — just enough to clean RSS descriptions.
    """
    import re
    clean = re.sub(r"<[^>]+>", " ", text)   # replace tags with space
    clean = re.sub(r"\s+", " ", clean)        # collapse whitespace
    return clean.strip()


# ── Main ──────────────────────────────────────────────────────────────────

def run_scraper():
    """
    Main scraper function.
    Loads sources, fetches articles, deduplicates, saves to raw_articles.json.
    """
    print(f"\n{'='*60}")
    print(f"  Scraper started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Load source config
    if not os.path.exists(SOURCES_FILE):
        print(f"[ERROR] {SOURCES_FILE} not found. Make sure it's in the same directory.")
        return

    with open(SOURCES_FILE, "r") as f:
        sources = json.load(f)

    # Load URLs already in digest.json to avoid re-summarizing
    seen_urls = load_existing_urls()
    print(f"Loaded {len(seen_urls)} already-seen URLs from {DIGEST_FILE}\n")

    # Fetch from all sources
    all_articles = []

    for source in sources:
        if source["type"] == "rss":
            articles = parse_rss_source(source, seen_urls)
        elif source["type"] == "api" and source["name"] == "Hacker News":
            articles = fetch_hacker_news(source, seen_urls)
        else:
            print(f"  [SKIP] Unknown source type: {source.get('type')} for {source.get('name')}")
            continue

        all_articles.extend(articles)

    # Save raw articles for analyzer.py
    with open(RAW_OUTPUT_FILE, "w") as f:
        json.dump(all_articles, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Scraper done. {len(all_articles)} raw articles saved to {RAW_OUTPUT_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_scraper()