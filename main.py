"""Entry point for rssfy-telegram."""

import asyncio

from rssfy.config import Config
from rssfy.index import generate_feeds_index
from rssfy.telegram import run_all


def main() -> None:
    config = Config.from_file("config.json")

    # Update RSS feeds
    asyncio.run(
        run_all(
            channels=config.channels,
            messages_to_fetch=config.messages_to_fetch,
            max_items=config.max_feed_items,
            github_repo=config.github_repository,
            github_branch=config.github_branch,
        )
    )

    # Regenerate the FEEDS.md index
    generate_feeds_index(channels=config.channels)


if __name__ == "__main__":
    main()
