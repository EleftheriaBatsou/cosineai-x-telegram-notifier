import json
import os
import pathlib
import sys
from typing import Dict, List, Optional

import requests

TWITTER_API_BASE = "https://api.twitter.com/2"
STATE_DIR = pathlib.Path("state")
STATE_FILE = STATE_DIR / "last_seen.json"


def _env(name: str, default: Optional[str] = None, required: bool = True) -> str:
    val = os.getenv(name, default)
    if required and not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return val


def get_user_id(username: str, bearer: str) -> Optional[str]:
    url = f"{TWITTER_API_BASE}/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer}"}
    params = {"user.fields": "id"}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    if resp.status_code == 429:
        # Rate limited, skip this run gracefully
        print(f"Rate limited fetching user id for {username}: {resp.status_code} {resp.text}", file=sys.stderr)
        return None
    if resp.status_code != 200:
        print(f"Error fetching user id for {username}: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    return data["data"]["id"]


def fetch_original_tweets(user_id: str, bearer: str, since_id: Optional[str]) -> List[Dict]:
    url = f"{TWITTER_API_BASE}/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {bearer}"}
    params = {
        "max_results": 20,
        "exclude": "replies,retweets",
        "tweet.fields": "created_at,referenced_tweets",
    }
    if since_id:
        params["since_id"] = since_id

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code == 429:
        # Rate limited; return no tweets so we don't fail the job
        print(f"Rate limited fetching tweets: {resp.status_code} {resp.text}", file=sys.stderr)
        return []
    if resp.status_code != 200:
        print(f"Error fetching tweets: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    payload = resp.json()
    tweets = payload.get("data", [])

    # Exclude quotes: if referenced_tweets contains a 'quoted' type, skip
    originals: List[Dict] = []
    for t in tweets:
        ref = t.get("referenced_tweets", [])
        if any(r.get("type") == "quoted" for r in ref):
            continue
        originals.append(t)

    # Sort oldest -> newest for sending in order
    originals.sort(key=lambda x: x["id"])
    return originals


def load_state() -> Dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: Dict[str, str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=20)
    if resp.status_code != 200:
        print(f"Telegram send error: {resp.status_code} {resp.text}", file=sys.stderr)


def main() -> None:
    twitter_bearer = _env("TWITTER_BEARER_TOKEN")
    telegram_bot_token = _env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _env("TELEGRAM_CHAT_ID")
    twitter_username = _env("TWITTER_USERNAME", "CosineAI", required=False)

    state = load_state()
    last_seen_id = state.get("last_seen_id")
    first_run = last_seen_id is None

    user_id = get_user_id(twitter_username, twitter_bearer)
    if not user_id:
        # Rate limited or temporary issue; skip this run without failing
        return

    tweets = fetch_original_tweets(user_id, twitter_bearer, last_seen_id)

    if first_run:
        # Initialize state to current latest original post without sending messages
        if tweets:
            newest_id = max(t["id"] for t in tweets)
            save_state({"last_seen_id": newest_id})
        else:
            # If no tweets returned (possible if user has no originals recently), set to latest available
            # Fetch without since_id to get the most recent original tweet
            fallback = fetch_original_tweets(user_id, twitter_bearer, since_id=None)
            if fallback:
                newest_id = max(t["id"] for t in fallback)
                save_state({"last_seen_id": newest_id})
        return

    if not tweets:
        # Nothing new or rate limited
        return

    # Send each new tweet in chronological order
    for t in tweets:
        tweet_id = t["id"]
        url = f"https://x.com/{twitter_username}/status/{tweet_id}"
        # X/Twitter API may omit text in some restricted cases; handle gracefully
        text = t.get("text", "")
        message = f"New post from @{twitter_username}:\n\n{text}\n\n{url}"
        send_telegram_message(telegram_bot_token, telegram_chat_id, message)

    newest_id = max(t["id"] for t in tweets)
    save_state({"last_seen_id": newest_id})


if __name__ == "__main__":
    main()