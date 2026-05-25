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

## Create Slack Token

1. Open https://api.slack.com/apps.
2. Click **Create New App**.
3. Choose **From scratch**.
4. Select your Slack workspace.
5. Open **OAuth & Permissions**.
6. Under **User Token Scopes**, add:
   - `im:history`
   - `users:read`
7. Click **Install to Workspace** or **Reinstall to Workspace**.
8. Copy the **User OAuth Token**. It starts with `xoxp-`.

## Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:

```bash
SLACK_USER_TOKEN=xoxp-your-token-here
```

Run the Slack export:

```bash
python slack_self_dm_exporter.py
```

## Output

Each run writes timestamped files and updates latest aliases:

- `self_dm_<timestamp>.json`
- `self_dm_<timestamp>.txt`
- `self_dm_latest.json`
- `self_dm_latest.txt`
- `manifest.json`

## Google Chat Webhook Test

For one private Google Chat Space, create an incoming webhook:

1. Open Google Chat.
2. Create or open a private Space, for example `Personal Notes - Ahmed`.
3. Click the Space name.
4. Open **Apps & integrations** or **Manage webhooks**.
5. Click **Add webhook**.
6. Name it, for example `Slack Notes Importer`.
7. Copy the webhook URL.

Add the webhook URL to `.env`:

```bash
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/...
```

Post only a few newest messages for formatting validation:

```bash
python google_chat_webhook_importer.py --limit 3
```

The exporter stores messages newest-first. The Google Chat test importer posts
oldest-to-newest so the Google Chat Space keeps the original Slack chronology.

The webhook import posts as the webhook app. The original Slack date is included
inside each message body.

## Rollout Notes

- Slack API limits are mainly per API method, per app, per workspace. If many
  employees use the same Slack app at the same time, some exports may receive
  `429` rate-limit responses. Wait and rerun later.
- Google Chat incoming webhooks are limited per Space. Keep `--delay` at `1.0`
  second or higher; `1.2` is safer for larger imports.
- For a company rollout, start with 5-10 users, then run the rest in batches.
