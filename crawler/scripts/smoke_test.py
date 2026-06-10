"""Smoke test: run a minimal real crawl against 591 + Supabase to verify end-to-end.

Usage: cd crawler && uv run python scripts/smoke_test.py
Runs against the live cloud Supabase (uses .env.local creds).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.config import FILTERS
from crawler.sources._591 import _591Source
from crawler.supabase_client import begin_run, finish_run, make_client, upsert_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("smoke")


def main() -> int:
    log.info("Filters: %s", FILTERS)

    # Test 1: Supabase connectivity
    log.info("=== Test 1: Supabase connectivity ===")
    client = make_client()
    resp = client.table("listings").select("count", count="exact").limit(1).execute()
    log.info("Current listings count: %s", resp.count)

    # Test 2: 591 source, max 1 page, max 3 detail fetches
    log.info("=== Test 2: 591 source (1 page, 3 details max) ===")
    src = _591Source(max_pages=1, headless=True)

    page = src._make_page()
    try:
        ids = src._collect_ids(page, FILTERS)
        log.info("Found %d IDs on page 1", len(ids))
        log.info("Sample IDs: %s", ids[:5])

        if not ids:
            log.warning("No IDs found — search may have returned 0 results")
            return 0

        # Fetch first 3 details
        listings = []
        for lid in ids[:3]:
            listing = src._fetch_detail(page, lid)
            if listing:
                log.info(
                    "Parsed: id=%s rooms=%d baths=%d price=%d district=%s title=%r",
                    listing.source_id, listing.rooms, listing.bathrooms,
                    listing.price, listing.district, listing.title[:30]
                )
                listings.append(listing)
    finally:
        page.quit()

    # Test 3: Filter + upsert
    log.info("=== Test 3: Filter + Supabase upsert ===")
    kept = [
        r for r in listings
        if r.rooms >= FILTERS.min_rooms
        and r.bathrooms >= FILTERS.min_bathrooms
        and r.price <= FILTERS.max_price
    ]
    log.info("After filter: %d / %d", len(kept), len(listings))

    run_id = begin_run(client, "591_smoke")
    found, new = upsert_listings(client, kept)
    finish_run(client, run_id, "success", found, new)
    log.info("Upserted: found=%d new=%d", found, new)

    # Verify
    resp = client.table("listings").select("count", count="exact").limit(1).execute()
    log.info("Listings count after: %s", resp.count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
