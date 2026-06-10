"""Smoke test: run only the Sinyi source end-to-end against real Supabase."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.config import FILTERS
from crawler.sources._sinyi import SinyiSource
from crawler.supabase_client import begin_run, finish_run, make_client, upsert_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("smoke-sinyi")


def main() -> int:
    log.info("Filters: %s", FILTERS)
    client = make_client()

    src = SinyiSource(max_pages=1, max_details_per_run=8)
    run_id = begin_run(client, src.name)
    listings = list(src.fetch(FILTERS))
    log.info("Raw: %d", len(listings))
    keep = [
        r for r in listings
        if r.rooms >= FILTERS.min_rooms
        and r.bathrooms >= FILTERS.min_bathrooms
        and r.price <= FILTERS.max_price
    ]
    log.info("After hard filter: %d / %d", len(keep), len(listings))
    for l in keep[:5]:
        log.info(
            "  %s: %s | NT$%d | %d房%d衛 | %s",
            l.source_id, l.title[:40], l.price, l.rooms, l.bathrooms, l.district,
        )
    found, new = upsert_listings(client, keep)
    finish_run(client, run_id, "success", found, new)
    log.info("Upserted: found=%d new=%d", found, new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
