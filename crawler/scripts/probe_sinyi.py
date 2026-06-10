"""Probe sinyi.com.tw rent search to understand the listing card markup
after JS rendering. Run with DrissionPage so we see what real users see.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from DrissionPage import ChromiumOptions, ChromiumPage


def main():
    opts = ChromiumOptions()
    opts.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.set_argument("--disable-blink-features=AutomationControlled")
    opts.headless()
    page = ChromiumPage(opts)

    try:
        # Taipei city, 3+ rooms, up to 120,000 rent, sort newest first
        url = (
            "https://www.sinyi.com.tw/rent/list/Taipei-city/"
            "3-up-room/0-120000-price/index.html?sort=time-desc"
        )
        print(f"GET {url}")
        page.get(url)
        page.wait.eles_loaded("css:.item_box", timeout=15)
        time.sleep(2)

        print(f"Title: {page.title}")
        print(f"URL after: {page.url}")

        # Find detail links — Sinyi uses /rent/houseno/C{id}
        links = page.eles("css:a[href*='houseno/C']")
        print(f"\nDetail links found: {len(links)}")
        ids: list[str] = []
        for el in links[:30]:
            href = el.attr("href") or ""
            m = re.search(r"houseno/(C\d+)", href)
            if m and m.group(1) not in ids:
                ids.append(m.group(1))
        print(f"Unique IDs: {len(ids)}")
        for i in ids[:8]:
            print(f"  {i}")

        # Inspect ONE detail page to find the structured selectors we need
        if ids:
            detail_url = f"https://www.sinyi.com.tw/rent/houseno/{ids[0]}"
            print(f"\nGET detail: {detail_url}")
            page.get(detail_url)
            time.sleep(3)

            print(f"Detail title: {page.title}")

            # Look for key fields
            for selector, label in [
                ("css:h1", "h1"),
                ("css:.house-info", "house-info"),
                ("css:.price", "price"),
                ("css:.detail_overview", "detail_overview"),
                ("css:meta[property='og:title']", "og:title"),
                ("css:meta[property='og:image']", "og:image"),
                ("css:meta[property='og:description']", "og:description"),
            ]:
                el = page.ele(selector, timeout=1)
                if el:
                    val = el.attr("content") or el.text or ""
                    print(f"  {label}: {val[:200]!r}")

            # Search the full rendered text for our key patterns
            body = page.ele("css:body")
            text = body.text if body else ""
            print()
            for pattern, label in [
                (r"[1-9]房[1-9]廳[1-9]衛", "layout"),
                (r"電梯[^,，\n]{0,15}|電梯華廈|電梯大樓", "elevator hint"),
                (r"租金[^0-9]*([0-9,]+)", "rent"),
                (r"台北市[^0-9\n]{1,15}區", "district"),
                (r"(套房|公寓|電梯華廈|電梯大樓|別墅|辦公|店面|廠房|車位)", "type"),
            ]:
                m = re.search(pattern, text)
                print(f"  {label}: {m.group(0) if m else 'NOT FOUND'!r}")

            # Save HTML for offline debug
            with open("/tmp/sinyi_detail.html", "w", encoding="utf-8") as f:
                f.write(page.html or "")
            print(f"\nDetail HTML saved to /tmp/sinyi_detail.html ({len(page.html or '')} bytes)")
    finally:
        page.quit()


if __name__ == "__main__":
    main()
