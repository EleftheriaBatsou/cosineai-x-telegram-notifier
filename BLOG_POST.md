# Automating CosineAI’s Tweets to Telegram: A Step‑by‑Step Guide You Can Replicate

I built a small automation that watches CosineAI’s X/Twitter account and sends a Telegram message to me when there’s a new original post (not replies, not retweets, not quotes). It runs every 6 hours via GitHub Actions, remembers what it already sent, and avoids duplications. This article documents exactly what we did, why, how much time it saves, and how you can reproduce it end‑to‑end.

## Why I did this (and how it saves time)

- No more manual checking: I don’t have to open X/Twitter several times a day. If CosineAI posts something new, I get it in Telegram automatically.
- Signal over noise: The bot filters out replies, retweets, and quotes—only original posts matter for me.
- Zero maintenance: It’s scheduled in GitHub Actions and commits minimal state back to the repo to remember the last seen tweet. It just keeps working.
- Portable and secure: All secrets live in GitHub Secrets (not in code). I can share the repo without exposing tokens.

Cosine (the Genie assistant) helped by scoping the problem, writing clean Python code, setting up the GitHub workflow, and documenting every step. That eliminated setup friction and prevented common pitfalls (e.g., token handling, chat ID discovery, state management).

---

## What the project does

- Monitors: https://x.com/CosineAI
- Interval: Every 6 hours (cron in GitHub Actions)
- Delivery: Sends Telegram messages via a bot to my chat
- Filters: Only original posts (excludes replies, retweets, and quotes)
- State: Remembers the last seen tweet ID and commits it to `state/last_seen.json` so duplicate alerts don’t happen

Repo files:
- `monitor.py` — the Python script that talks to Twitter/X and Telegram
- `requirements.txt` — Python dependency list
- `.github/workflows/monitor.yml` — GitHub Actions workflow (schedule + run + commit state)
- `README.md` — concise setup instructions
- `state/` — folder storing `last_seen.json` (automatically updated by the workflow)

---

## Links you’ll need

- Twitter/X Developer portal: https://developer.twitter.com/
- Twitter/X v2 API reference (Users and Tweets): https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet
- Telegram BotFather (create bot): https://t.me/BotFather
- Telegram sendMessage API: https://core.telegram.org/bots/api#sendmessage
- Telegram getUpdates (to find chat ID): https://core.telegram.org/bots/api#getupdates  
  Direct pattern for your bot: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
- GitHub Actions docs: https://docs.github.com/en/actions
- actions/checkout: https://github.com/actions/checkout
- actions/setup-python: https://github.com/actions/setup-python
- Python Requests: https://requests.readthedocs.io/en/latest/

---

## Step‑by‑step: How to replicate this project

### 1) Create a GitHub repository and add files
- Create a new repo (public or private).
- Add these files (you can copy from the project):
  - `monitor.py`, `requirements.txt`, `README.md`, `.github/workflows/monitor.yml`, and a `state/` directory (empty to start).

What they do:
- `monitor.py` reads environment variables (your bearer token, bot token, chat id, username).
- It fetches the latest original tweets (excludes replies/retweets/quotes).
- It sends Telegram messages for any new posts since the last run.
- The workflow commits `state/last_seen.json` when it changes so the bot knows what it already sent.

### 2) Get your Twitter/X API v2 Bearer Token
- Go to https://developer.twitter.com/ and create a developer account if you don’t have one.
- Create an app and enable access to v2 endpoints that allow fetching user tweets (`GET /2/users/:id/tweets`).
- Copy the Bearer token (App‑only auth). You’ll store this in GitHub Secrets as `TWITTER_BEARER_TOKEN`.

Docs starting points:
- https://developer.twitter.com/en/docs/twitter-api
- Tweet object model and fields: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet

### 3) Create a Telegram bot and get its token
- Open Telegram and talk to @BotFather: https://t.me/BotFather
- Use `/newbot` to create a bot; BotFather will give you a token (format looks like `1234567890:ABC...XYZ`).
- You’ll store this in GitHub Secrets as `TELEGRAM_BOT_TOKEN`.

### 4) Find your Telegram chat ID
You need the numeric chat ID to send messages to yourself or a group.

Option A: Direct messages to your bot
- Send any message to your bot in Telegram (e.g., “hi”).
- Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a browser.
- Find `"chat":{"id":...}` in the JSON response. That number is your `TELEGRAM_CHAT_ID`.

Option B: Group chats
- Add your bot to a Telegram group and send a message.
- Use the same `getUpdates` URL and locate the group’s chat ID in the JSON.

Reference: https://core.telegram.org/bots/api#getupdates

### 5) Set GitHub Secrets for the workflow
In your repo, go to Settings → Secrets and variables → Actions → “New repository secret” and create:
- `TWITTER_BEARER_TOKEN` — your Bearer token from step 2
- `TELEGRAM_BOT_TOKEN` — your Bot token from step 3
- `TELEGRAM_CHAT_ID` — your chat ID from step 4
- `TWITTER_USERNAME` — optional; defaults to `CosineAI`. Set to any username you want to monitor.

### 6) Enable GitHub Actions and confirm permissions
- Actions is enabled by default; make sure your repo allows the workflow to commit contents (for private repos, ensure `permissions: contents: write` is set in the workflow—this project already includes that).
- The workflow file `.github/workflows/monitor.yml` has:
  - A 6‑hour cron schedule: `0 */6 * * *`
  - A manual trigger via “Run workflow”
  - Steps to:
    - Checkout code
    - Set up Python
    - Install dependencies
    - Run `python monitor.py`
    - Commit `state/last_seen.json` when it changes

### 7) First run behavior (so you don’t get spammed)
- On the first run, the script initializes the state to the most recent original post without sending any Telegram message.
- After that, it only sends messages for posts that appear after the recorded `last_seen_id`.

### 8) Local testing (optional)
If you want to run it locally before enabling Actions:
- Use Python 3.10+.
- Export env vars:
  ```
  export TWITTER_BEARER_TOKEN=...
  export TELEGRAM_BOT_TOKEN=...
  export TELEGRAM_CHAT_ID=...
  export TWITTER_USERNAME=CosineAI
  ```
- Install dependencies:
  ```
  pip install -r requirements.txt
  ```
- Run:
  ```
  python monitor.py
  ```

### 9) Customize it
- Change `TWITTER_USERNAME` to monitor any account.
- Adjust the cron schedule in `.github/workflows/monitor.yml` (e.g., every hour).
- Edit filters if you want to include quotes or replies (the code currently excludes both).

---

## Troubleshooting

- Twitter API errors (401/403/429):
  - Confirm your Bearer token works and your app has correct access.
  - Check rate limits; you may need to reduce frequency or increase app level.
- Telegram message not delivered:
  - Verify `TELEGRAM_CHAT_ID` by checking the JSON at `getUpdates` again.
  - Make sure the bot is not blocked and can post in the chat/group.
- No state updates:
  - Ensure the workflow has `permissions: contents: write`.
  - Check that `state/last_seen.json` exists after the first successful run (it’s created by the workflow when needed).

---

## How Cosine (Genie) helped

- Designed the flow to be resilient (first‑run state initialization, chronological send order).
- Implemented clean code with minimal dependencies (`requests` only).
- Set up GitHub Actions with proper permissions and a safe commit step for `state/last_seen.json`.
- Documented the exact steps to obtain tokens/IDs and secure them via GitHub Secrets.

This kind of assistance compresses hours of trial‑and‑error into minutes, and gives a repeatable result. It’s especially helpful for small automations that you want to “set and forget.”

---

## Reuse checklist

- Repo created with provided files
- Secrets set:
  - `TWITTER_BEARER_TOKEN`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `TWITTER_USERNAME` (optional)
- Actions enabled; workflow present
- First run: state initialized quietly
- Subsequent runs: new original posts are delivered to Telegram

That’s it. Fork it, set secrets, and you’re done.