"""Convert Telethon Message objects into plain entry dicts for feedgen."""

from __future__ import annotations

from datetime import timezone
from typing import Any

from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityCode,
    MessageEntityEmail,
    MessageEntityItalic,
    MessageEntityMentionName,
    MessageEntityPre,
    MessageEntitySpoiler,
    MessageEntityStrike,
    MessageEntityTextUrl,
    MessageEntityUnderline,
    MessageEntityUrl,
    MessageMediaDocument,
    MessageMediaPhoto,
)


def message_url(channel: str, msg_id: int) -> str:
    """Return the canonical public URL for a Telegram message."""
    return f"https://t.me/{channel}/{msg_id}"


def _entities_to_html(text: str, entities: list | None) -> str:
    """
    Convert a Telegram message text + entities list into an HTML string.

    Supported entity types:
        Bold        -> <b>
        Italic      -> <i>
        Underline   -> <u>
        Strike      -> <s>
        Code        -> <code>
        Pre         -> <pre>
        Spoiler     -> <span style="background:#000;color:#000"> (hidden text)
        TextUrl     -> <a href="...">
        Url         -> <a href="..."> (auto-detected URL)
        Email       -> <a href="mailto:...">
        MentionName -> <a href="tg://user?id=...">

    Entities may overlap (e.g. bold + italic on the same range). The
    implementation processes the text character-by-character, tracking which
    tags are open at each position, which correctly handles overlapping ranges.
    """
    if not text:
        return ""

    entities = entities or []

    # Build per-character open/close tag lists
    opens: dict[int, list[str]] = {}
    closes: dict[int, list[str]] = {}

    for ent in entities:
        offset = ent.offset
        end = ent.offset + ent.length

        if isinstance(ent, MessageEntityBold):
            open_tag, close_tag = "<b>", "</b>"
        elif isinstance(ent, MessageEntityItalic):
            open_tag, close_tag = "<i>", "</i>"
        elif isinstance(ent, MessageEntityUnderline):
            open_tag, close_tag = "<u>", "</u>"
        elif isinstance(ent, MessageEntityStrike):
            open_tag, close_tag = "<s>", "</s>"
        elif isinstance(ent, MessageEntityCode):
            open_tag, close_tag = "<code>", "</code>"
        elif isinstance(ent, MessageEntityPre):
            lang = getattr(ent, "language", "") or ""
            open_tag = f'<pre><code class="language-{lang}">' if lang else "<pre>"
            close_tag = "</code></pre>" if lang else "</pre>"
        elif isinstance(ent, MessageEntitySpoiler):
            open_tag = '<span style="background:#000;color:#000">'
            close_tag = "</span>"
        elif isinstance(ent, MessageEntityTextUrl):
            href = ent.url.replace('"', "&quot;")
            open_tag, close_tag = f'<a href="{href}">', "</a>"
        elif isinstance(ent, MessageEntityUrl):
            # The URL is the text itself; we'll wrap it after escaping
            url_text = text[offset:end]
            href = url_text.replace('"', "&quot;")
            open_tag, close_tag = f'<a href="{href}">', "</a>"
        elif isinstance(ent, MessageEntityEmail):
            email_text = text[offset:end]
            open_tag, close_tag = f'<a href="mailto:{email_text}">', "</a>"
        elif isinstance(ent, MessageEntityMentionName):
            user_id = ent.user_id
            open_tag, close_tag = f'<a href="tg://user?id={user_id}">', "</a>"
        else:
            continue  # unsupported entity — render as plain text

        opens.setdefault(offset, []).append(open_tag)
        closes.setdefault(end, []).append(close_tag)

    # Walk through the text, inserting tags and HTML-escaping characters
    result: list[str] = []
    for i, ch in enumerate(text):
        # Close tags in reverse order (innermost first), then open new ones
        for tag in reversed(closes.get(i, [])):
            result.append(tag)
        for tag in opens.get(i, []):
            result.append(tag)
        # HTML-escape the character
        if ch == "&":
            result.append("&amp;")
        elif ch == "<":
            result.append("&lt;")
        elif ch == ">":
            result.append("&gt;")
        else:
            result.append(ch)

    # Flush any closing tags at the very end (innermost first)
    for tag in reversed(closes.get(len(text), [])):
        result.append(tag)

    return "".join(result)


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
        title       — first line of text (plain), truncated to 80 chars
        link        — same as id
        description — HTML with inline formatting; photos rendered as <img> tags
        pub_date    — timezone-aware datetime (UTC)
    """
    url = message_url(channel, msg.id)
    text: str = msg.message or ""

    # Title: first non-empty line (plain text), capped at 80 characters
    first_line = text.split("\n")[0].strip()
    if len(first_line) > 80:
        title = first_line[:77] + "..."
    else:
        title = first_line or f"Post #{msg.id}"

    # HTML description: photos first, then formatted text
    description_parts: list[str] = []

    if image_urls:
        for img_url in image_urls:
            description_parts.append(
                f'<p><img src="{img_url}" alt="Photo" style="max-width:100%;"></p>'
            )
    elif isinstance(msg.media, MessageMediaPhoto):
        description_parts.append("<p>[Photo]</p>")
    elif isinstance(msg.media, MessageMediaDocument):
        description_parts.append("<p>[Document/Video]</p>")

    if text:
        html_text = _entities_to_html(text, getattr(msg, "entities", None))
        description_parts.append(html_text.replace("\n", "<br>\n"))

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
