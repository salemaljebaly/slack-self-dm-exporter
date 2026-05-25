#!/usr/bin/env python3
"""
Export the authenticated Slack user's self-DM messages to JSON and TXT.

This tool is intentionally read-only. It does not delete, post, or modify
Slack data.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from http.client import IncompleteRead
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.error

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler

from utils.colors import format_stats_table, print_header, print_info, print_success, print_warning
from utils.progress import ActivityIndicator


class SlackSelfDMExporter:
    """Exports the current user's Slack self-DM conversation."""

    def __init__(self, token: str, output_dir: str = "exports", config: Optional[Dict[str, Any]] = None):
        self.client = WebClient(
            token=token,
            retry_handlers=[RateLimitErrorRetryHandler(max_retry_count=3)],
        )
        self.output_dir = Path(output_dir)
        self.config = config or {}
        self.logger = self._setup_logging()
        self.user_info = self._auth_test()

    def _setup_logging(self) -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("slack_self_dm_exporter.log"),
                logging.StreamHandler(),
            ],
        )
        return logging.getLogger(__name__)

    def _auth_test(self) -> Dict[str, Any]:
        try:
            response = self.client.auth_test()
            if not response.get("ok"):
                raise RuntimeError(f"Slack auth failed: {response.get('error')}")
            return dict(response.data)
        except SlackApiError as exc:
            raise RuntimeError(f"Slack auth failed: {exc.response.get('error')}") from exc

    @property
    def user_id(self) -> str:
        return self.user_info["user_id"]

    @property
    def team_name(self) -> str:
        return self.user_info.get("team") or "unknown-team"

    @property
    def team_id(self) -> str:
        return self.user_info.get("team_id") or "unknown-team-id"

    def open_self_dm(self) -> str:
        """Open or resume the user's self-DM and return its channel ID."""
        try:
            response = self.client.conversations_open(
                users=self.user_id,
                return_im=True,
                prevent_creation=False,
            )
            if not response.get("ok"):
                raise RuntimeError(f"Could not open self-DM: {response.get('error')}")
            return response["channel"]["id"]
        except SlackApiError as exc:
            raise RuntimeError(f"Could not open self-DM: {exc.response.get('error')}") from exc

    def fetch_history(self, channel_id: str) -> List[Dict[str, Any]]:
        """Fetch every message from the self-DM, oldest first."""
        max_retries = int(self.config.get("max_retries", 3))
        retry_delay = float(self.config.get("retry_delay_seconds", 2))
        request_delay = float(self.config.get("request_delay_seconds", 0.8))
        page_limit = int(self.config.get("page_limit", 200))

        messages: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        api_call_count = 0
        spinner = ActivityIndicator("Fetching self-DM history", show_elapsed=True)
        spinner.start()

        try:
            while True:
                response = None
                for attempt in range(max_retries):
                    try:
                        response = self.client.conversations_history(
                            channel=channel_id,
                            limit=page_limit,
                            cursor=cursor,
                            inclusive=True,
                        )
                        api_call_count += 1
                        break
                    except (IncompleteRead, urllib.error.URLError, ConnectionError, OSError) as exc:
                        if attempt >= max_retries - 1:
                            raise
                        wait_time = retry_delay * (attempt + 1)
                        self.logger.warning(
                            "Network error on conversations_history attempt %s/%s: %s",
                            attempt + 1,
                            max_retries,
                            exc,
                        )
                        time.sleep(wait_time)

                if response is None or not response.get("ok"):
                    error = response.get("error") if response else "no_response"
                    raise RuntimeError(f"Could not fetch self-DM history: {error}")

                batch = list(response.get("messages", []))
                messages.extend(batch)
                spinner.update_message(
                    f"Fetching self-DM history ({len(messages)} messages, {api_call_count} API calls)"
                )

                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                time.sleep(request_delay)
        finally:
            spinner.stop()

        messages.sort(key=lambda item: float(item.get("ts", 0)), reverse=True)
        return messages

    def export(self) -> Dict[str, Any]:
        channel_id = self.open_self_dm()
        messages = self.fetch_history(channel_id)
        normalized_messages = [self._normalize_message(message) for message in messages]

        export_root = self.output_dir / self._safe_path_part(self.team_name) / self.user_id
        export_root.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        json_path = export_root / f"self_dm_{timestamp}.json"
        txt_path = export_root / f"self_dm_{timestamp}.txt"
        latest_json_path = export_root / "self_dm_latest.json"
        latest_txt_path = export_root / "self_dm_latest.txt"
        manifest_path = export_root / "manifest.json"

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "team": {
                "id": self.team_id,
                "name": self.team_name,
            },
            "user": {
                "id": self.user_id,
                "name": self.user_info.get("user"),
            },
            "conversation": {
                "id": channel_id,
                "type": "self_dm",
            },
            "message_count": len(normalized_messages),
            "messages": normalized_messages,
        }

        self._write_json(json_path, payload)
        self._write_json(latest_json_path, payload)
        self._write_text(txt_path, normalized_messages)
        self._write_text(latest_txt_path, normalized_messages)

        manifest = {
            "latest_json": str(latest_json_path),
            "latest_txt": str(latest_txt_path),
            "last_timestamped_json": str(json_path),
            "last_timestamped_txt": str(txt_path),
            "message_count": len(normalized_messages),
            "exported_at": payload["exported_at"],
            "team_id": self.team_id,
            "team_name": self.team_name,
            "user_id": self.user_id,
            "conversation_id": channel_id,
        }
        self._write_json(manifest_path, manifest)
        return manifest

    def _normalize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        ts = message.get("ts", "")
        normalized = {
            "ts": ts,
            "datetime": self._slack_ts_to_iso(ts),
            "type": message.get("type"),
            "subtype": message.get("subtype"),
            "user": message.get("user"),
            "text": message.get("text", ""),
            "thread_ts": message.get("thread_ts"),
            "reply_count": message.get("reply_count", 0),
            "reactions": message.get("reactions", []),
            "files": self._normalize_files(message.get("files", [])),
            "attachments": message.get("attachments", []),
            "raw": message,
        }
        return normalized

    def _normalize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_files = []
        for file_obj in files:
            normalized_files.append(
                {
                    "id": file_obj.get("id"),
                    "name": file_obj.get("name"),
                    "title": file_obj.get("title"),
                    "mimetype": file_obj.get("mimetype"),
                    "filetype": file_obj.get("filetype"),
                    "url_private": file_obj.get("url_private"),
                    "permalink": file_obj.get("permalink"),
                    "created": file_obj.get("created"),
                    "timestamp": file_obj.get("timestamp"),
                }
            )
        return normalized_files

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    def _write_text(self, path: Path, messages: List[Dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as file_handle:
            for message in messages:
                timestamp = message.get("datetime") or message.get("ts")
                text = (message.get("text") or "").replace("\r\n", "\n").replace("\r", "\n")
                file_handle.write(f"[{timestamp}] {text}\n")
                for file_obj in message.get("files", []):
                    title = file_obj.get("title") or file_obj.get("name") or file_obj.get("id")
                    url = file_obj.get("permalink") or file_obj.get("url_private") or ""
                    file_handle.write(f"  file: {title} {url}\n")
                file_handle.write("\n")

    def _slack_ts_to_iso(self, ts: str) -> Optional[str]:
        if not ts:
            return None
        try:
            return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()
        except ValueError:
            return None

    def _safe_path_part(self, value: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
        return clean.strip("-") or "unknown"


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    load_dotenv()
    token = os.getenv("SLACK_USER_TOKEN")
    if not token:
        raise RuntimeError("SLACK_USER_TOKEN is required in .env")

    output_dir = os.getenv("EXPORT_DIR", "exports")
    config = {
        "page_limit": int(os.getenv("PAGE_LIMIT", "200")),
        "request_delay_seconds": float(os.getenv("REQUEST_DELAY_SECONDS", "0.8")),
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "retry_delay_seconds": float(os.getenv("RETRY_DELAY_SECONDS", "2")),
        "download_files": _parse_bool(os.getenv("DOWNLOAD_FILES"), False),
    }

    print_header("Slack Self-DM Exporter")
    print_info("Mode: read-only export")

    exporter = SlackSelfDMExporter(token=token, output_dir=output_dir, config=config)
    manifest = exporter.export()

    print_success("Export complete")
    print(format_stats_table(manifest))

    if manifest["message_count"] == 0:
        print_warning("The self-DM was exported, but it did not contain messages.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
