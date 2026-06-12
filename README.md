# rssfy-telegram

Convert Telegram channels to RSS Feeds — automatically, every 30 minutes, via GitHub Actions.

Each public Telegram channel gets its own RSS feed file committed to this repository, accessible via raw GitHub URLs.

---

## How It Works

1. A GitHub Actions cron job runs every 30 minutes.
2. [`main.py`](main.py) connects to Telegram using the [Telethon](https://github.com/LonamiWebs/Telethon) library and a pre-generated `StringSession`.
3. For each channel in [`config.json`](config.json), it fetches the latest messages.
4. New messages (not already in the feed) are prepended to the existing feed.
5. The feed is trimmed to `max_feed_items` to prevent unbounded growth.
6. Updated feed files are committed back to the repository under `feeds/`.

---

## Setup

### 1. Get Telegram API Credentials

1. Go to [https://my.telegram.org](https://my.telegram.org) and log in.
2. Click **API development tools**.
3. Create a new application (any name/platform is fine).
4. Note your **App api_id** and **App api_hash**.

### 2. Generate a StringSession

Run the helper script **once** on your local machine:

```bash
pip install telethon
python generate_session.py
```

Follow the prompts (enter your `api_id`, `api_hash`, and phone number). After completing the SMS login, the script will print a long `StringSession` string. **Copy it — you will need it in the next step.**

### 3. Add GitHub Repository Secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name                | Value                                      |
|----------------------------|--------------------------------------------|
| `TELEGRAM_API_ID`          | Your integer API ID from my.telegram.org   |
| `TELEGRAM_API_HASH`        | Your API hash string from my.telegram.org  |
| `TELEGRAM_SESSION_STRING`  | The string printed by `generate_session.py`|

### 4. Configure Channels

Edit [`config.json`](config.json) to list the public Telegram channels you want to follow:

```json
{
  "channels": [
    "telegram",
    "durov"
  ],
  "max_feed_items": 10,
  "messages_to_fetch": 10,
  "github_repository": "your-username/your-repo",
  "github_branch": "main"
}
```

| Key                  | Description                                                                                      |
|----------------------|--------------------------------------------------------------------------------------------------|
| `channels`           | List of public Telegram channel usernames (without `@`)                                          |
| `max_feed_items`     | Number of most recent posts to keep per feed (default: `10`)                                     |
| `messages_to_fetch`  | How many recent messages to fetch from Telegram per run (default: `10`)                          |
| `github_repository`  | Your GitHub repo in `owner/repo` form — used to build raw image URLs. Can be left empty (`""`) to use the `GITHUB_REPOSITORY` env var set automatically by GitHub Actions. |
| `github_branch`      | Branch where feeds are committed (default: `"main"`)                                             |

### 5. Subscribe to a Feed

Use the raw GitHub URL to subscribe in any RSS reader:

```
https://raw.githubusercontent.com/<username>/<repo>/main/feeds/<channel>.xml
```

---

## Running Locally

```bash
pip install -r requirements.txt

export TELEGRAM_API_ID=12345678
export TELEGRAM_API_HASH=your_api_hash_here
export TELEGRAM_SESSION_STRING=your_session_string_here

python main.py
```

Generated feeds will be written to the `feeds/` directory.

---

## Project Structure

```
.
├── config.json                        # Channel list and settings
├── main.py                            # Thin entry point
├── generate_session.py                # One-time session string generator
├── requirements.txt                   # Python dependencies
├── FEEDS.md                           # Auto-generated index of all feed URLs
├── feeds/                             # Generated RSS feed files (auto-committed)
│   ├── telegram.xml
│   ├── durov.xml
│   └── media/                         # Full-quality downloaded photos
│       ├── telegram/
│       │   └── <msg_id>.jpg
│       └── durov/
│           └── <msg_id>.jpg
├── rssfy/                             # Core package
│   ├── __init__.py
│   ├── config.py                      # Config dataclass & loader
│   ├── feed.py                        # RSS feed load / build / save helpers
│   ├── index.py                       # FEEDS.md generator
│   ├── parser.py                      # Telegram message → feed entry conversion
│   └── telegram.py                    # Telethon client & per-channel processing
└── .github/
    └── workflows/
        └── update_feeds.yml           # GitHub Actions workflow
```

---

## Dependencies

| Package    | Purpose                              |
|------------|--------------------------------------|
| `telethon` | Telegram MTProto client & media download |
| `feedgen`  | RSS/Atom feed generation             |
| `lxml`     | Fast XML parsing and generation      |
