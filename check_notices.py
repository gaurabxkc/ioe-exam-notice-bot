#!/usr/bin/env python3
"""
Checks the IOE Examination Control Division notice page for new notices
and posts any new ones to a Discord channel via webhook.

State (which notice IDs have already been seen) is stored in seen_notices.json.
The GitHub Actions workflow commits this file back to the repo after every run,
so the bot remembers what it already announced.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- Config -----------------------------------------------------------------

# The real notice-list page for this site.
NOTICE_URLS = [
    "https://exam.ioe.tu.edu.np/notices",
]

STATE_FILE = Path(__file__).parent / "seen_notices.json"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# Matches links like /notices/13392 and captures the numeric ID
NOTICE_LINK_RE = re.compile(r"/notices/(\d+)(?:[/?]|$)")


# --- Core logic ---------------------------------------------------------------

def fetch_notices():
    """Fetch and parse the notice list. Returns a list of dicts:
    {"id": "13392", "title": "...", "url": "https://.../notices/13392"}
    ordered as they appear on the page (site lists newest first).
    """
    last_error = None
    for base_url in NOTICE_URLS:
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            last_error = e
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        notices = []
        seen_ids_on_page = set()

        for a in soup.find_all("a", href=True):
            m = NOTICE_LINK_RE.search(a["href"])
            if not m:
                continue
            notice_id = m.group(1)
            if notice_id in seen_ids_on_page:
                continue  # some pages link the same notice twice (row + "read more")
            title = a.get_text(strip=True)
            if not title:
                # fall back to the title attribute or nearby text
                title = a.get("title", "").strip() or f"Notice {notice_id}"
            full_url = "https://exam.ioe.tu.edu.np/notices/" + notice_id
            notices.append({"id": notice_id, "title": title, "url": full_url})
            seen_ids_on_page.add(notice_id)

        if notices:
            return notices

    if last_error:
        raise RuntimeError(f"Could not fetch notice page: {last_error}")
    raise RuntimeError(
        "Fetched page(s) successfully but found no notice links. "
        "The site's HTML structure may have changed."
    )


def load_seen_ids():
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return set(data.get("seen_ids", []))
        except (json.JSONDecodeError, OSError):
            return set()
    return None  # None means "no state file yet" (first run)


def save_seen_ids(ids):
    STATE_FILE.write_text(
        json.dumps({"seen_ids": sorted(ids, key=int)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def send_discord_message(notice):
    if not DISCORD_WEBHOOK_URL:
        print("WARNING: DISCORD_WEBHOOK_URL not set, skipping Discord post.")
        return
    payload = {
        "embeds": [
            {
                "title": notice["title"][:250],
                "url": notice["url"],
                "description": "📢 New notice published on IOE Examination Control Division",
                # "color": 3447003,
                "color": 15105570,
            }
        ]
    }
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code >= 300:
        print(f"Discord webhook failed ({resp.status_code}): {resp.text}", file=sys.stderr)
    else:
        print(f"Posted to Discord: {notice['title']}")


def run_test_mode():
    """Send the single most recent real notice to Discord as a test post.
    Does NOT read or write seen_notices.json, so it has zero effect on
    normal tracking -- safe to run as many times as you like.
    """
    notices = fetch_notices()
    if not notices:
        print("No notices found to test with.")
        return
    latest = notices[0]
    print(f"TEST MODE: sending latest notice to Discord: {latest['title']}")
    payload = {
        "embeds": [
            {
                "title": latest["title"][:250],
                "url": latest["url"],
                "description": "🧪 Test message (this notice was already known, sent for testing only)",
                "color": 15105570,
            }
        ]
    }
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL is not set.", file=sys.stderr)
        sys.exit(1)
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code >= 300:
        print(f"Discord webhook failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("Test message sent successfully. Check your Discord channel!")


def main():
    if os.environ.get("TEST_MODE", "").lower() == "true":
        run_test_mode()
        return

    notices = fetch_notices()
    current_ids = {n["id"] for n in notices}

    previously_seen = load_seen_ids()

    if previously_seen is None:
        # First ever run: just record the current state, don't spam Discord
        # with the entire notice history.
        print(f"First run. Recording {len(current_ids)} existing notices as seen, no Discord posts.")
        save_seen_ids(current_ids)
        return

    new_notices = [n for n in notices if n["id"] not in previously_seen]

    if not new_notices:
        print("No new notices.")
    else:
        # Post oldest-first so the channel reads in chronological order
        for notice in reversed(new_notices):
            send_discord_message(notice)

    save_seen_ids(previously_seen | current_ids)


if __name__ == "__main__":
    main()
