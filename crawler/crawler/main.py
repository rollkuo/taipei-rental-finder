"""Crawler entry point.

Run: `cd crawler && uv run python -m crawler.main`
or  `uv run python main.py` (from inside crawler/)
"""

from __future__ import annotations

import logging
import sys
import traceback

# Allow running both as module (-m crawler.main) and as script (python main.py)
if __package__ in (None, ""):
    # Script mode — add parent of crawler/ to sys.path so 'crawler' is importable
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.config import FILTERS
from crawler.notify import notify_discord
from crawler.sources._591 import _591Source
from crawler.supabase_client import begin_run, finish_run, make_client, upsert_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("crawler")


def run_source(source, filters) -> tuple[int, int]:
    """Iterate source, apply final filter, upsert. Returns (found, new)."""
    client = make_client()
    run_id = begin_run(client, source.name)
    try:
        raw_listings = list(source.fetch(filters))
        # Apply final hard filter (in case source over-returns)
        keep = [
            r for r in raw_listings
            if r.rooms >= filters.min_rooms
            and r.bathrooms >= filters.min_bathrooms
            and r.price <= filters.max_price
        ]
        log.info("%s: %d raw → %d after filter", source.name, len(raw_listings), len(keep))
        found, new = upsert_listings(client, keep)
        finish_run(client, run_id, "success", found, new)
        return found, new
    except Exception as e:
        tb = traceback.format_exc()
        log.error("%s failed: %s", source.name, tb)
        finish_run(client, run_id, "failed", 0, 0, error=str(e)[:1000])
        notify_discord(f"⚠️ 爬蟲 `{source.name}` 失敗:\n```\n{tb[-1500:]}\n```")
        raise


def main() -> int:
    sources = [_591Source()]
    failures = 0
    for src in sources:
        try:
            found, new = run_source(src, FILTERS)
            log.info("%s done: found=%d new=%d", src.name, found, new)
        except Exception:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
