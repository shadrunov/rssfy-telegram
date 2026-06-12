"""Telethon client setup and per-channel processing logic."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

from .feed import FEEDS_DIR, MEDIA_DIR, build_feed, load_existing_entries, load_existing_ids, save_feed
from .parser import message_to_entry, message_url


def _build_client() -> TelegramClient:
    """
    Build a TelegramClient from environment variables.

    Required env vars:
        TELEGRAM_API_ID          — integer app ID from https://my.telegram.org
        TELEGRAM_API_HASH        — string app hash from https://my.telegram.org
        TELEGRAM_SESSION_STRING  — StringSession produced by generate_session.py
    """
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session_string = os.environ["TELEGRAM_SESSION_STRING"]
    return TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
        system_lang_code="en-US",
        lang_code="en",
    )


def _raw_github_url(repo: str, branch: str, rel_path: Path) -> str:
    """
    Build a raw.githubusercontent.com URL for a file in the repository.

    Args:
        repo:     GitHub repository in the form "owner/repo".
        branch:   Branch name (e.g. "main").
        rel_path: Path relative to the repository root.
    """
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path.as_posix()}"


async def _download_photo(client: TelegramClient, msg, channel: str) -> Path | None:
    """
    Download the photo attached to a message to feeds/media/<channel>/<msg_id>.jpg.

    Returns the local Path on success, or None if the download fails.
    Skips re-download if the file already exists from a previous run.
    """
    media_channel_dir = MEDIA_DIR / channel
    media_channel_dir.mkdir(parents=True, exist_ok=True)
    dest = media_channel_dir / f"{msg.id}.jpg"

    if dest.exists():
        return dest  # already downloaded in a previous run

    try:
        await client.download_media(msg, file=str(dest))
        return dest
    except Exception as exc:
        print(f"    [warn] Could not download photo for message {msg.id}: {exc}")
        return None


def _group_messages(messages: list) -> list[list]:
    """
    Group messages into logical posts.

    Telegram albums (multiple photos in one post) share the same `grouped_id`.
    Each group becomes a single RSS feed entry. Standalone messages (no
    grouped_id) form single-message groups.

    Returns a list of groups, each group being a list of Message objects
    sorted by message ID (ascending). Groups are ordered by the ID of their
    first message (descending — newest first, matching Telethon's default order).
    """
    grouped: dict[int, list] = defaultdict(list)
    standalone: list[list] = []

    for msg in messages:
        if msg.grouped_id:
            grouped[msg.grouped_id].append(msg)
        else:
            standalone.append([msg])

    album_groups = [sorted(g, key=lambda m: m.id) for g in grouped.values()]
    all_groups = standalone + album_groups
    all_groups.sort(key=lambda g: g[0].id, reverse=True)
    return all_groups


async def process_channel(
    client: TelegramClient,
    channel: str,
    messages_to_fetch: int,
    max_items: int,
    github_repo: str,
    github_branch: str,
) -> None:
    """
    Fetch new messages for a single channel and update its RSS feed file.

    Steps:
      1. Load existing feed (if any) to get already-seen message IDs.
      2. Fetch the latest `messages_to_fetch` messages from Telegram.
      3. Group messages into logical posts (albums share a grouped_id).
      4. Filter to only groups whose representative message is not yet in the feed.
      5. For each new group, download all photos and build raw GitHub URLs.
      6. Merge new + old entries, deduplicate, trim to max_items (keeps last N posts).
      7. Write the updated feed to feeds/<channel>.xml.
    """
    print(f"Processing @{channel} ...")
    feed_path = FEEDS_DIR / f"{channel}.xml"

    # 1. Load existing data
    existing_ids = load_existing_ids(feed_path)
    old_entries = load_existing_entries(feed_path)
    print(f"  Existing items in feed: {len(old_entries)}")

    # 2. Fetch latest messages from Telegram
    try:
        entity = await client.get_entity(channel)
        channel_title: str = getattr(entity, "title", f"@{channel}")
    except Exception as exc:
        print(f"  [error] Could not get entity for @{channel}: {exc}")
        return

    messages = await client.get_messages(entity, limit=messages_to_fetch)
    print(f"  Fetched {len(messages)} messages from Telegram")

    # 3. Group into logical posts (albums + standalone)
    groups = _group_messages(list(messages))

    # 4. Filter to only new groups (representative = first message in group)
    new_groups = [
        group for group in groups
        if message_url(channel, group[0].id) not in existing_ids
    ]
    print(f"  New posts to add: {len(new_groups)} (from {len(groups)} grouped posts)")

    if not new_groups and old_entries:
        print("  No new posts — feed unchanged.")
        return

    # 5. Build entry dicts, downloading all photos per group
    new_entries: list[dict] = []
    for group in new_groups:
        representative = group[0]  # first message carries the text and date
        image_urls: list[str] = []

        if github_repo:
            for msg in group:
                if isinstance(msg.media, MessageMediaPhoto):
                    local_path = await _download_photo(client, msg, channel)
                    if local_path:
                        image_urls.append(
                            _raw_github_url(github_repo, github_branch, local_path)
                        )

        entry = message_to_entry(channel, representative, image_urls=image_urls or None)

        if entry["description"] == "(no text)":
            print(f"  - skipped {entry['link']} (no text, no media)")
            continue

        new_entries.append(entry)

        album_note = f" (album, {len(group)} msgs)" if len(group) > 1 else ""
        photos_note = f", {len(image_urls)} photo(s)" if image_urls else ""
        text_preview = (representative.text or "").replace("\n", " ")[:60]
        text_note = ('-- "' + text_preview + '..."') if text_preview else ""
        print(f"  + {entry['link']}{album_note}{photos_note}{text_note}")

    # 6 & 7. Build and save the updated feed
    fg = build_feed(channel, channel_title, new_entries, old_entries, max_items)
    path = save_feed(fg, channel)
    print(f"  Saved feed -> {path}")


async def run_all(
    channels: list[str],
    messages_to_fetch: int,
    max_items: int,
    github_repo: str,
    github_branch: str,
) -> None:
    """Connect to Telegram (as a user account) and process all configured channels."""
    async with _build_client() as client:
        for channel in channels:
            try:
                await process_channel(
                    client,
                    channel,
                    messages_to_fetch,
                    max_items,
                    github_repo,
                    github_branch,
                )
            except Exception as exc:
                print(f"  [error] Failed to process @{channel}: {exc}")
