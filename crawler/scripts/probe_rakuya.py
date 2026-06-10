"""Probe rakuya.com.tw with DrissionPage to see if it bypasses Cloudflare.

Usage: uv run python scripts/probe_rakuya.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from DrissionPage import ChromiumOptions, ChromiumPage


def main():
    opts = ChromiumOptions()
    # NON-headless — Cloudflare typically lets visible browsers through
    opts.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.set_argument("--disable-blink-features=AutomationControlled")
    # opts.headless()  # disabled — let's see if visible browser passes CF
    page = ChromiumPage(opts)

    try:
        url = "https://rent.rakuya.com.tw/result?city=01"
        print(f"GET {url}")
        page.get(url)
        # Cloudflare challenge can take 10-25 seconds
        for i in range(6):
            time.sleep(5)
            t = page.title or ""
            print(f"  [{(i+1)*5}s] Title: {t!r}")
            if "Just a moment" not in t and "Cloudflare" not in t:
                break

        print(f"Final Title: {page.title}")
        print(f"URL after: {page.url}")
        html_len = len(page.html or "")
        print(f"HTML length: {html_len}")

        # Look for listing item links — rakuya uses /item/{id}
        items = page.eles("css:a[href*='/item/']")
        print(f"\nItem links found: {len(items)}")
        for el in items[:5]:
            href = el.attr("href") or ""
            print(f"  href: {href}")

        # Save HTML for offline inspection
        with open("/tmp/rakuya_search.html", "w", encoding="utf-8") as f:
            f.write(page.html or "")
        print(f"\nFull HTML saved to /tmp/rakuya_search.html ({html_len} bytes)")

        # Try a detail page
        if items:
            detail_href = items[0].attr("href")
            print(f"\nGET detail: {detail_href}")
            page.get(detail_href)
            time.sleep(5)
            print(f"Detail title: {page.title}")
            detail_html_len = len(page.html or "")
            print(f"Detail HTML length: {detail_html_len}")
            with open("/tmp/rakuya_detail.html", "w", encoding="utf-8") as f:
                f.write(page.html or "")
            print(f"Detail HTML saved to /tmp/rakuya_detail.html ({detail_html_len} bytes)")
    finally:
        page.quit()


if __name__ == "__main__":
    main()
