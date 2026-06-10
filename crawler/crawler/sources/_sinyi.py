"""信義房屋 (sinyi.com.tw) rental scraper.

Sinyi uses path-based URL filtering and renders enough content server-side
that the listing IDs (format: C\\d+) appear as direct hrefs.

Filter URL example:
  https://www.sinyi.com.tw/rent/list/Taipei-city/3-up-room/0-120000-price/index.html?sort=time-desc

Detail URL: https://www.sinyi.com.tw/rent/houseno/{listing_id}

Each detail page has a structured og:title:
  "台北市文山區元利公館河景三房車位，租金58,000，立即了解更多租屋資訊"
which we mine for district + rent. Bedroom count comes from "X房Y廳Z衛".
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from DrissionPage import ChromiumOptions, ChromiumPage

from ..config import Filters
from ..models import RawListing

log = logging.getLogger(__name__)

LIST_URL_TEMPLATE = (
    "https://www.sinyi.com.tw/rent/list/Taipei-city/"
    "{min_rooms}-up-room/0-{max_price}-price/index.html?sort=time-desc"
)
DETAIL_URL_TEMPLATE = "https://www.sinyi.com.tw/rent/houseno/{listing_id}"

_LISTING_ID_RE = re.compile(r"houseno/(C\d+)")
_LAYOUT_RE = re.compile(r"([1-9])房(\d+)廳([1-9])衛")
# Rent from og:title: "...，租金58,000，..."
_RENT_FROM_TITLE_RE = re.compile(r"租金([\d,]+)")
# District from breadcrumb-ish text or title: "台北市XX區"
_DISTRICT_RE = re.compile(r"台北市[>]?([^>\s,，0-9]{1,4}區)")

# Property types we want to EXCLUDE from results — Sinyi mixes residential
# with commercial. Title or page-text matches trigger a skip.
_BLOCKED_TYPES = ("辦公", "商辦", "店面", "廠房", "倉庫", "土地")


class SinyiSource:
    name = "sinyi"

    def __init__(
        self,
        max_pages: int = 3,
        headless: bool = True,
        detail_sleep_seconds: float = 4.0,
        max_details_per_run: int = 40,
    ):
        self.max_pages = max_pages
        self.headless = headless
        self.detail_sleep_seconds = detail_sleep_seconds
        self.max_details_per_run = max_details_per_run

    def _build_list_url(self, filters: Filters) -> str:
        return LIST_URL_TEMPLATE.format(
            min_rooms=filters.min_rooms,
            max_price=filters.max_price,
        )

    def _build_list_url_page(self, filters: Filters, page_num: int) -> str:
        """Page 1 has no suffix; subsequent pages use `/p{n}` before `index.html`."""
        base = self._build_list_url(filters)
        if page_num <= 1:
            return base
        return base.replace("/index.html", f"/{page_num}-page/index.html")

    def _make_page(self) -> ChromiumPage:
        opts = ChromiumOptions()
        if self.headless:
            opts.headless()
        opts.set_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        opts.set_argument("--no-sandbox")
        opts.set_argument("--disable-blink-features=AutomationControlled")
        return ChromiumPage(opts)

    def fetch(self, filters: Filters) -> Iterator[RawListing]:
        page = self._make_page()
        seen_ids: set[str] = set()
        details_fetched = 0
        consecutive_failures = 0
        try:
            for page_num in range(1, self.max_pages + 1):
                if details_fetched >= self.max_details_per_run:
                    log.info("sinyi: hit max_details_per_run=%d", self.max_details_per_run)
                    break
                ids = self._collect_ids(page, filters, page_num)
                new_ids = [i for i in ids if i not in seen_ids]
                seen_ids.update(new_ids)
                log.info(
                    "sinyi page %d: %d IDs (%d new)",
                    page_num, len(ids), len(new_ids),
                )
                if not new_ids:
                    break  # ran out of results
                for lid in new_ids:
                    if details_fetched >= self.max_details_per_run:
                        break
                    listing = self._fetch_detail(page, lid)
                    details_fetched += 1
                    if listing is not None:
                        consecutive_failures = 0
                        yield listing
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= 5:
                            log.warning(
                                "sinyi: 5 consecutive failures, stopping early "
                                "after %d details",
                                details_fetched,
                            )
                            return
                    time.sleep(self.detail_sleep_seconds)
        finally:
            try:
                page.quit()
            except Exception:
                pass

    def _collect_ids(
        self, page: ChromiumPage, filters: Filters, page_num: int
    ) -> list[str]:
        url = self._build_list_url_page(filters, page_num)
        log.info("sinyi list URL: %s", url)
        try:
            page.get(url)
            page.wait.eles_loaded("css:a[href*='houseno/C']", timeout=15)
        except Exception as e:
            log.warning("sinyi list page %d failed to load: %s", page_num, e)
            return []
        elements = page.eles("css:a[href*='houseno/C']")
        ids: list[str] = []
        seen: set[str] = set()
        for el in elements:
            href = el.attr("href") or ""
            m = _LISTING_ID_RE.search(href)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                ids.append(m.group(1))
        return ids

    def _fetch_detail(self, page: ChromiumPage, listing_id: str) -> RawListing | None:
        url = DETAIL_URL_TEMPLATE.format(listing_id=listing_id)
        try:
            page.get(url)
            page.wait.eles_loaded("css:h1, css:meta[property='og:title']", timeout=10)
        except Exception as e:
            log.warning("sinyi detail %s failed: %s", listing_id, e)
            return None

        payload: dict[str, Any] = {"listing_id": listing_id}

        # og:title — best source of structured title + price + district
        og_title_el = page.ele("css:meta[property='og:title']", timeout=1)
        og_title = og_title_el.attr("content") if og_title_el else None
        h1_el = page.ele("css:h1", timeout=1)
        h1_text = h1_el.text.strip() if h1_el else ""
        title = h1_text or (og_title.split("，")[0] if og_title else f"信義房屋 {listing_id}")
        payload["title_raw"] = title
        payload["og_title"] = og_title

        # Exclude commercial listings
        check_text = f"{og_title or ''} {title}"
        if any(blocked in check_text for blocked in _BLOCKED_TYPES):
            log.info("sinyi %s: skip commercial (%s)", listing_id, title[:30])
            return None

        # Price from og:title
        price: int | None = None
        if og_title:
            m = _RENT_FROM_TITLE_RE.search(og_title)
            if m:
                try:
                    price = int(m.group(1).replace(",", ""))
                except ValueError:
                    price = None
        if price is None or price <= 0:
            log.warning("sinyi %s: no price parsed from og_title=%r", listing_id, og_title)
            return None

        # Layout (X房Y廳Z衛) from page body text
        body = page.ele("css:body", timeout=1)
        body_text = body.text if body else ""
        layout = _LAYOUT_RE.search(body_text)
        if not layout:
            log.warning("sinyi %s: no layout found", listing_id)
            return None
        rooms = int(layout.group(1))
        bathrooms = int(layout.group(3))
        if rooms > 9 or bathrooms > 9:
            log.warning("sinyi %s: implausible rooms/baths %d/%d", listing_id, rooms, bathrooms)
            return None

        # District — try og:title first, fall back to body text
        district: str | None = None
        for source_text in (og_title or "", body_text):
            m = _DISTRICT_RE.search(source_text)
            if m:
                district = m.group(1)
                break
        if not district:
            log.warning("sinyi %s: no Taipei district found", listing_id)
            return None

        # Image from og:image (sinyi sometimes uses a placeholder, but a URL is better than null)
        img_el = page.ele("css:meta[property='og:image']", timeout=1)
        image_url = img_el.attr("content") if img_el else None
        if image_url and "og_img.jpg" in image_url:
            # Default placeholder, prefer first actual listing photo
            actual_img = page.ele("css:img[src*='res.sinyi.com.tw/rent']", timeout=1)
            if actual_img:
                image_url = actual_img.attr("src") or image_url

        return RawListing(
            source="sinyi",
            source_id=listing_id,
            url=url,
            title=title,
            price=price,
            rooms=rooms,
            bathrooms=bathrooms,
            district=district,
            road=None,  # Sinyi address parsing is brittle, skip for now
            has_elevator=True,  # No reliable filter; assume yes for the units that pass other gates
            image_url=image_url,
            posted_at=datetime.now(timezone.utc),
            scraped_payload=payload,
        )
