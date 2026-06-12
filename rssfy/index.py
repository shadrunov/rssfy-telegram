"""Generate FEEDS.md — a Markdown index of all RSS feed files."""

from __future__ import annotations

from pathlib import Path


def generate_feeds_index(
    channels: list[str],
    output_path: Path = Path("FEEDS.md"),
) -> None:
    """
    Write FEEDS.md with a table listing every channel and its local RSS feed path.

    Args:
        channels:    List of Telegram channel usernames.
        output_path: Destination path for the generated Markdown file.
    """
    lines: list[str] = [
        "# RSS Feeds",
        "",
        "Auto-generated index of all Telegram channel RSS feeds.",
        "",
        "| Channel | Telegram | RSS Feed |",
        "|---------|----------|----------|",
    ]

    for channel in channels:
        telegram_url = f"https://t.me/{channel}"
        feed_cell = f"`feeds/{channel}.xml`"
        lines.append(f"| @{channel} | [{telegram_url}]({telegram_url}) | {feed_cell} |")

    lines += [
        "",
        "---",
        "",
        "_This file is automatically updated on every run of `main.py`._",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated {output_path}")
