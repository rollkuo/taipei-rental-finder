"""Supabase write client: upsert listings, log crawl_runs."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timezone

from supabase import Client, create_client

from .config import supabase_service_key, supabase_url
from .models import RawListing

log = logging.getLogger(__name__)


def make_client() -> Client:
    return create_client(supabase_url(), supabase_service_key())


def begin_run(client: Client, source: str) -> str:
    """Insert a crawl_runs row in status=running. Returns run_id."""
    resp = (
        client.table("crawl_runs")
        .insert({"source": source, "status": "running"})
        .execute()
    )
    return resp.data[0]["id"]


def finish_run(
    client: Client,
    run_id: str,
    status: str,
    found_count: int,
    new_count: int,
    error: str | None = None,
) -> None:
    client.table("crawl_runs").update({
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "found_count": found_count,
        "new_count": new_count,
        "error": error,
    }).eq("id", run_id).execute()


def upsert_listings(
    client: Client, listings: Iterable[RawListing]
) -> tuple[int, int]:
    """Upsert listings. Returns (found_count, new_count).

    - new_count = rows that didn't exist before (first_seen_at == now)
    - deleted_at IS NOT NULL rows are NOT touched (server-side filter via WHERE)
    """
    found = 0
    new = 0
    for raw in listings:
        found += 1
        row = raw.to_db_row()
        # Check if this listing exists and is deleted — skip if so
        existing = (
            client.table("listings")
            .select("id, deleted_at")
            .eq("source", row["source"])
            .eq("source_id", row["source_id"])
            .limit(1)
            .execute()
        )
        if existing.data:
            existing_row = existing.data[0]
            if existing_row.get("deleted_at"):
                log.info("skip deleted: %s/%s", row["source"], row["source_id"])
                continue
            # Update — preserve saved_at, refresh last_seen_at + mutable fields
            client.table("listings").update({
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "price": row["price"],
                "title": row["title"],
                "image_url": row["image_url"],
                "scraped_payload": row["scraped_payload"],
            }).eq("id", existing_row["id"]).execute()
        else:
            client.table("listings").insert(row).execute()
            new += 1
    return found, new
