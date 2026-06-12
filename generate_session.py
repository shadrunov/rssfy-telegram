"""
Run this script ONCE locally to generate a Telethon StringSession for a user account.
Save the printed session string as the TELEGRAM_SESSION_STRING GitHub Secret.

Prerequisites:
  1. Obtain API_ID and API_HASH from https://my.telegram.org.

Usage:
    python generate_session.py
"""

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def _generate(api_id: int, api_hash: str) -> str:
    async with TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        system_lang_code="en-US",
        lang_code="en",
    ) as client:
        return client.session.save()


def main() -> None:
    api_id = int(input("Enter your API_ID (from https://my.telegram.org): ").strip())
    api_hash = input("Enter your API_HASH (from https://my.telegram.org): ").strip()

    print("You will now be prompted to log in with your Telegram account (phone number + SMS code).")
    session_string = asyncio.run(_generate(api_id, api_hash))

    print("\n" + "=" * 60)
    print("Your StringSession (save this as TELEGRAM_SESSION_STRING):")
    print("=" * 60)
    print(session_string)
    print("=" * 60 + "\n")
    print("Store these values as GitHub Repository Secrets:")
    print(f"  TELEGRAM_API_ID          = {api_id}")
    print(f"  TELEGRAM_API_HASH        = {api_hash}")
    print(f"  TELEGRAM_SESSION_STRING  = <string above>")


if __name__ == "__main__":
    main()
