"""Convert Telethon Message objects into plain entry dicts for feedgen."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto


def message_url(channel: str, msg_id: int) -> str:
    """Return the canonical public URL for a Telegram message."""
    return f"https://t.me/{channel}/{msg_id}"


def message_to_entry(
    channel: str,
    msg: Any,
    image_urls: list[str] | None = None,
) -> dict:
    """
    Convert a Telethon Message to a plain dict suitable for feedgen.

    Args:
        channel:    Telegram channel username.
        msg:        Telethon Message object (the first/representative message
                    of an album group, or a standalone message).
        image_urls: Optional list of direct URLs to full-quality photos for
                    this entry (e.g. raw GitHub URLs). Each URL becomes an
                    <img> tag in the description, in order.

    Keys returned:
        id          — unique URL used as the feed item GUID
        title       — first line of text, truncated to 80 chars
        link        — same as id
        description — HTML-escaped full text; photos rendered as <img> tags
        pub_date    — timezone-aware datetime (UTC)
    """
    url = message_url(channel, msg.id)
    text: str = msg.message or ""

    # Title: first non-empty line, capped at 80 characters
    first_line = text.split("\n")[0].strip()
    if len(first_line) > 80:
        title = first_line[:77] + "…"
    else:
        title = first_line or f"Post #{msg.id}"

    # HTML description: photos first, then text
    description_parts: list[str] = []

    if image_urls:
        # Render all photos in the album
        for img_url in image_urls:
            description_parts.append(
                f'<p><img src="{img_url}" alt="Photo" style="max-width:100%;"></p>'
            )
    elif isinstance(msg.media, MessageMediaPhoto):
        # Photo present but no direct URL available
        description_parts.append("<p>[Photo]</p>")
    elif isinstance(msg.media, MessageMediaDocument):
        description_parts.append("<p>[Document/Video]</p>")

    if text:
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        description_parts.append(escaped.replace("\n", "<br>\n"))

    description = "\n".join(description_parts) or "(no text)"

    # Ensure pub_date is timezone-aware
    pub_date = msg.date
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)

    return {
        "id": url,
        "title": title,
        "link": url,
        "description": description,
        "pub_date": pub_date,
    }
