"""RSS feed helpers: load existing feed, build updated feed, save to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from feedgen.feed import FeedGenerator
from lxml import etree


FEEDS_DIR = Path("feeds")
MEDIA_DIR = FEEDS_DIR / "media"


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def load_existing_ids(feed_path: Path) -> set[str]:
    """
    Return the set of item GUIDs already present in an RSS feed file.
    Returns an empty set if the file does not exist or cannot be parsed.
    """
    if not feed_path.exists():
        return set()
    try:
        tree = etree.parse(str(feed_path))
        root = tree.getroot()
        # RSS 2.0: //channel/item/guid
        guids = {el.text for el in root.findall(".//guid") if el.text}
        # Atom: //entry/id
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        ids = {el.text for el in root.findall(".//atom:id", ns) if el.text}
        return guids | ids
    except Exception as exc:
        print(f"  [warn] Could not parse existing feed {feed_path}: {exc}")
        return set()


def load_existing_entries(feed_path: Path) -> list[dict]:
    """
    Parse an existing RSS feed file and return a list of entry dicts so that
    historical items can be re-added to the new FeedGenerator.
    Returns an empty list if the file does not exist or cannot be parsed.
    """
    if not feed_path.exists():
        return []
    try:
        tree = etree.parse(str(feed_path))
        root = tree.getroot()

        def _text(item: Any, tag: str) -> str:
            el = item.find(tag)
            return el.text if el is not None else ""

        return [
            {
                "id": _text(item, "guid"),
                "title": _text(item, "title"),
                "link": _text(item, "link"),
                "description": _text(item, "description"),
                "pubdate": _text(item, "pubDate"),
            }
            for item in root.findall(".//item")
        ]
    except Exception as exc:
        print(f"  [warn] Could not load existing entries from {feed_path}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Build & save
# ---------------------------------------------------------------------------

def build_feed(
    channel: str,
    channel_title: str,
    new_entries: list[dict],
    old_entries: list[dict],
    max_items: int,
) -> FeedGenerator:
    """
    Construct a FeedGenerator with new entries prepended to old ones.

    Steps:
      1. Merge new + old entries (new first).
      2. Deduplicate by entry id.
      3. Trim to max_items (keeps the most recent posts).
    """
    fg = FeedGenerator()
    fg.id(f"https://t.me/{channel}")
    fg.title(channel_title or f"@{channel}")
    fg.link(href=f"https://t.me/{channel}", rel="alternate")
    fg.description(f"RSS feed for Telegram channel @{channel}")
    fg.language("en")

    # 1. Merge: new entries first (newest at top), then historical entries
    all_entries = new_entries + old_entries

    # 2. Deduplicate by id, preserving order
    seen: set[str] = set()
    unique: list[dict] = []
    for entry in all_entries:
        eid = entry.get("id") or entry.get("link", "")
        if eid not in seen:
            seen.add(eid)
            unique.append(entry)

    # 3. Trim to max_items
    for entry in unique[:max_items]:
        fe = fg.add_entry(order="append")
        fe.id(entry["id"])
        fe.title(entry["title"])
        fe.link(href=entry["link"])
        fe.description(entry.get("description", ""))
        if "pub_date" in entry:
            fe.pubDate(entry["pub_date"])
        elif entry.get("pubdate"):
            # Re-parsed from existing XML — feedgen accepts RFC 2822 strings
            fe.pubDate(entry["pubdate"])

    return fg


def save_feed(fg: FeedGenerator, channel: str) -> Path:
    """Write the feed as RSS XML to feeds/<channel>.xml and return the path."""
    FEEDS_DIR.mkdir(exist_ok=True)
    feed_path = FEEDS_DIR / f"{channel}.xml"
    fg.rss_file(str(feed_path), pretty=True)
    return feed_path
