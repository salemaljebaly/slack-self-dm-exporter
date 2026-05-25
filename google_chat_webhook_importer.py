#!/usr/bin/env python3
"""
Post a small batch of exported Slack self-DM messages to a Google Chat webhook.

This is intended for testing formatting before a larger import. The webhook URL
must be provided through GOOGLE_CHAT_WEBHOOK_URL and is never stored in git.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request

from dotenv import load_dotenv

from utils.colors import format_stats_table, print_header, print_info, print_success, print_warning


MAX_CHAT_MESSAGE_LENGTH = 3900


def load_export(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def format_chat_message(message: Dict[str, Any], index: int, total: int) -> str:
    slack_date = message.get("datetime") or message.get("ts") or "unknown date"
    text = (message.get("text") or "").strip()
    files = message.get("files") or []

    if not text and files:
        text = "(file attachment)"
    elif not text:
        text = "(empty message)"

    lines = [
        f"*Slack note {index}/{total}*",
        f"Original date: {slack_date}",
        "",
        text,
    ]

    for file_obj in files:
        title = file_obj.get("title") or file_obj.get("name") or file_obj.get("id") or "file"
        url = file_obj.get("permalink") or file_obj.get("url_private")
        if url:
            lines.extend(["", f"File: {title}", url])
        else:
            lines.extend(["", f"File: {title}"])

    formatted = "\n".join(lines)
    if len(formatted) > MAX_CHAT_MESSAGE_LENGTH:
        return formatted[: MAX_CHAT_MESSAGE_LENGTH - 40] + "\n\n...[truncated for Google Chat test]"
    return formatted


def post_to_webhook(webhook_url: str, text: str, max_retries: int = 3) -> None:
    payload = json.dumps({"text": text}).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=UTF-8"}

    for attempt in range(max_retries):
        req = request.Request(webhook_url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                if 200 <= response.status < 300:
                    return
                raise RuntimeError(f"Google Chat webhook returned HTTP {response.status}")
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries - 1:
                retry_after = int(exc.headers.get("Retry-After", "5"))
                time.sleep(retry_after)
                continue
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Google Chat webhook failed: HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Google Chat webhook network error: {exc}") from exc


def select_messages(messages: List[Dict[str, Any]], limit: int, offset: int) -> List[Dict[str, Any]]:
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    if offset < 0:
        raise ValueError("--offset must be 0 or greater")
    return messages[offset : offset + limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Post a small Slack self-DM export batch to Google Chat.")
    parser.add_argument(
        "--export",
        default="exports/Lamah/U01BG066ZSB/self_dm_latest.json",
        help="Path to self_dm_latest.json",
    )
    parser.add_argument("--limit", type=int, default=3, help="Number of messages to post")
    parser.add_argument("--offset", type=int, default=0, help="Number of exported messages to skip")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between webhook posts in seconds")
    args = parser.parse_args()

    load_dotenv()
    webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("GOOGLE_CHAT_WEBHOOK_URL is required in .env")

    export_path = Path(args.export)
    export_data = load_export(export_path)
    messages = export_data.get("messages", [])
    selected_messages = select_messages(messages, args.limit, args.offset)

    print_header("Google Chat Webhook Test Import")
    print_info(f"Export file: {export_path}")
    print_info(f"Posting {len(selected_messages)} message(s)")

    for index, message in enumerate(selected_messages, start=1):
        post_to_webhook(
            webhook_url,
            format_chat_message(message, index=index, total=len(selected_messages)),
        )
        print_success(f"Posted message {index}/{len(selected_messages)}")
        if index < len(selected_messages):
            time.sleep(args.delay)

    print_success("Google Chat test import complete")
    print(format_stats_table({"posted": len(selected_messages), "offset": args.offset, "limit": args.limit}))
    if len(selected_messages) < args.limit:
        print_warning("Fewer messages were available than requested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
