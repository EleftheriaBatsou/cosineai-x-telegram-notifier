# Automating CosineAI’s Tweets to Telegram: A Step‑by‑Step Guide You Can Replicate
I built a small automation that watches CosineAI’s X/Twitter account and sends a Telegram message to me when there’s a new original post (not replies, not retweets, not quotes). It runs every 6 hours via GitHub Actions, remembers what it already sent, and avoids duplications. This article documents exactly what we did, why, how much time it saves, and how you can reproduce it end‑to‑end.
## Why I did this (and how it saves time)
- No more