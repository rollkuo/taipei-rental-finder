"""Discord webhook notifier — no-op if DISCORD_WEBHOOK_URL is unset."""

import logging
import requests

from .config import discord_webhook_url

log = logging.getLogger(__name__)


def notify_discord(message: str) -> None:
    url = discord_webhook_url()
    if not url:
        log.info("Discord webhook unset, skipping notify: %s", message[:80])
        return
    try:
        requests.post(url, json={"content": message[:1900]}, timeout=10)
    except Exception as e:
        log.warning("Discord notify failed: %s", e)
