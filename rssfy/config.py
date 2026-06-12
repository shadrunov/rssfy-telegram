"""Configuration loading for rssfy."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    channels: list[str]
    max_feed_items: int = 10
    messages_to_fetch: int = 10
    # GitHub repository in the form "owner/repo".
    # Falls back to the GITHUB_REPOSITORY env var (set automatically in Actions).
    github_repository: str = ""
    # Branch where feeds are committed (default: "main").
    github_branch: str = "main"

    @classmethod
    def from_file(cls, path: str | Path = "config.json") -> "Config":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_path.open() as f:
            data = json.load(f)

        # github_repository: prefer config file value, then env var
        github_repository = data.get("github_repository") or os.environ.get("GITHUB_REPOSITORY", "")

        return cls(
            channels=data.get("channels", []),
            max_feed_items=data.get("max_feed_items", 10),
            messages_to_fetch=data.get("messages_to_fetch", 10),
            github_repository=github_repository,
            github_branch=data.get("github_branch", "main"),
        )
