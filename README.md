# Slack Self-DM Exporter

Read-only exporter for the authenticated Slack user's self-DM notes.

## What It Does

- Authenticates with `SLACK_USER_TOKEN`.
- Opens the current user's self-DM.
- Fetches the full message history with pagination and retry handling.
- Writes JSON and TXT files under `exports/<team>/<user_id>/`.
- Does not delete, post, or modify Slack data.

## Required Slack Scopes

Use a Slack User OAuth Token with:

- `im:history`
- `users:read`

If file downloads are added later, also use `files:read`.

## Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python slack_self_dm_exporter.py
```

This project already has a copied `.env` when created from the local
`slack-test` project.

## Output

Each run writes timestamped files and updates latest aliases:

- `self_dm_<timestamp>.json`
- `self_dm_<timestamp>.txt`
- `self_dm_latest.json`
- `self_dm_latest.txt`
- `manifest.json`

## Google Chat Webhook Test

For one private Google Chat Space, create an incoming webhook and add it to
`.env` as `GOOGLE_CHAT_WEBHOOK_URL`.

Post only a few newest messages for formatting validation:

```bash
python google_chat_webhook_importer.py --limit 3
```

The webhook import posts as the webhook app. The original Slack date is included
inside each message body.
