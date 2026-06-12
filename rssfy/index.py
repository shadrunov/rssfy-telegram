"""Generate FEEDS.md — a Markdown index of all RSS feed files."""

from __future__ import annotations

from pathlib import Path


def generate_feeds_index(
    channels: list[str],
    github_repo: str,
    github_branch: str,
    output_path: Path = Path("FEEDS.md"),
) -> None:
    """
    Write FEEDS.md with a table listing every channel and its RSS feed URL.

    Args:
        channels:      List of Telegram channel usernames.
        github_repo:   GitHub repository in "owner/repo" form.
        github_branch: Branch name (e.g. "main").
        output_path:   Destination path for the generated Markdown file.
    """
    lines: list[str] = [
        "# RSS Feeds",
        "",
        "Auto-generated index of all Telegram channel RSS feeds.",
        "",
        "| Channel | RSS Feed |",
        "|---------|----------|",
    ]

    for channel in channels:
        raw_url = (
            f"https://raw.githubusercontent.com/{github_repo}"
            f"/refs/heads/{github_branch}/feeds/{channel}.xml"
        )
        feed_cell = f"[`feeds/{channel}.xml`]({raw_url})"
        lines.append(f"| @{channel} | {feed_cell} |")

    lines += [
        "",
        "---",
        "",
        "_This file is automatically updated on every run of `main.py`._",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated {output_path}")
