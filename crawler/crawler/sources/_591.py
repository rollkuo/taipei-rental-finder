"""591 rent scraper using DrissionPage (CDP-based, evades navigator.webdriver detection).

Two-stage approach (proven by ceshine/591scraper):
  1. fetch_listing_ids: Open search list page → collect listing IDs (paginate)
  2. fetch_detail: For each ID, open detail page → extract structured fields

Search URL params for 591 rent:
  region=1                 # 台北市
  kind=1                   # 整層住家
  rentprice=,120000        # 月租上限
  other=lift               # 必須有電梯
  order=posttime           # 依上架時間排序
  orderType=desc           # 新→舊
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

LIST_URL_BASE = "https://rent.591.com.tw/list"
DETAIL_URL_TEMPLATE = "https://rent.591.com.tw/{listing_id}"

# Regex for extracting listing ID from URL: /12345.html or /12345
_LISTING_ID_RE = re.compile(r"/(\d+)(?:\.html)?(?:[?#]|$)")
# Structured "X房Y廳Z衛" pattern — match all three together to anchor against text like "591租屋"
_LAYOUT_PATTERN = re.compile(r"([1-9])房(\d+)廳([1-9])衛")
# Fallback single-field patterns: digit 1-9 only, with non-digit guards on both sides
_ROOM_PATTERN = re.compile(r"(?<!\d)([1-9])房(?!\d)")
_BATH_PATTERN = re.compile(r"(?<!\d)([1-9])衛(?!\d)")
# Regex for price like "30,000" or "30000"
_PRICE_RE = re.compile(r"([\d,]+)")
# Taipei districts (12)
TAIPEI_DISTRICTS = {
    "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區",
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區",
}


class _591Source:
    name = "591"

    def __init__(self, max_pages: int = 5, headless: bool = True):
        self.max_pages = max_pages
        self.headless = headless

    def _build_search_url(self, filters: Filters) -> str:
        params = [
            f"region={filters.city_region_id}",
            f"kind={filters.kind}",
            f"rentprice=,{filters.max_price}",
            "order=posttime",
            "orderType=desc",
        ]
        if filters.require_elevator:
            params.append("other=lift")
        return LIST_URL_BASE + "?" + "&".join(params)

    def _make_page(self) -> ChromiumPage:
        opts = ChromiumOptions()
        if self.headless:
            opts.headless()
        # Anti-detection: realistic user agent + viewport
        opts.set_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        opts.set_argument("--no-sandbox")
        opts.set_argument("--disable-blink-features=AutomationControlled")
        return ChromiumPage(opts)

    def fetch(self, filters: Filters) -> Iterator[RawListing]:
        """Two-stage crawl. Yields RawListing instances (pre-filter)."""
        page = self._make_page()
        try:
            listing_ids = self._collect_ids(page, filters)
            log.info("591: collected %d listing IDs", len(listing_ids))
            for lid in listing_ids:
                listing = self._fetch_detail(page, lid)
                if listing is not None:
                    yield listing
                time.sleep(1.5)  # be polite
        finally:
            try:
                page.quit()
            except Exception:
                pass

    def _collect_ids(self, page: ChromiumPage, filters: Filters) -> list[str]:
        url = self._build_search_url(filters)
        log.info("591 list URL: %s", url)
        page.get(url)
        page.wait.eles_loaded("css:.item-info-title a", timeout=10)

        ids: list[str] = []
        seen: set[str] = set()
        for page_num in range(1, self.max_pages + 1):
            elements = page.eles("css:.item-info-title a")
            for el in elements:
                href = el.attr("href") or ""
                match = _LISTING_ID_RE.search(href)
                if match and match.group(1) not in seen:
                    seen.add(match.group(1))
                    ids.append(match.group(1))

            # Try next page. DrissionPage returns a falsy NoneElement (not Python None)
            # when not found, so use truthiness rather than `is None`.
            next_btn = page.ele("text:下一頁", timeout=2)
            if not next_btn:
                break
            try:
                href = (next_btn.attr("href") or "").strip()
            except Exception:
                href = ""
            if not href or href == "#":
                break
            try:
                next_btn.click()
                page.wait.eles_loaded("css:.item-info-title a", timeout=10)
                time.sleep(1.0)
            except Exception:
                break
        return ids

    def _fetch_detail(self, page: ChromiumPage, listing_id: str) -> RawListing | None:
        url = DETAIL_URL_TEMPLATE.format(listing_id=listing_id)
        try:
            page.get(url)
            page.wait.eles_loaded("css:.title h1", timeout=10)
        except Exception as e:
            log.warning("591 detail fetch failed for %s: %s", listing_id, e)
            return None

        payload: dict[str, Any] = {"listing_id": listing_id}

        title_el = page.ele("css:.title h1", timeout=2)
        title = title_el.text.strip() if title_el else ""
        payload["title_raw"] = title

        # Price: e.g., "55,000" 元/月
        price_el = page.ele("css:.house-price", timeout=2)
        price_text = price_el.text if price_el else ""
        payload["price_raw"] = price_text
        price = _parse_price(price_text)
        if price is None:
            log.warning("591 %s: no price parsed from %r", listing_id, price_text)
            return None

        # Rooms / bathrooms - prefer the structured "X房Y廳Z衛" pattern from visible page text
        # (page.html includes attributes / ng-* values that contain spurious digits next to 房/衛).
        body_el = page.ele("css:body", timeout=1)
        page_text = body_el.text if body_el else ""
        layout_match = _LAYOUT_PATTERN.search(page_text)
        if layout_match:
            rooms = int(layout_match.group(1))
            bathrooms = int(layout_match.group(3))
        else:
            rooms = _first_int(_ROOM_PATTERN, page_text)
            bathrooms = _first_int(_BATH_PATTERN, page_text)
        if rooms is None or bathrooms is None or rooms > 9 or bathrooms > 9:
            log.warning("591 %s: invalid rooms/baths (r=%s b=%s)", listing_id, rooms, bathrooms)
            return None

        # Address & district
        addr_el = page.ele("css:div.address div", timeout=2)
        addr_text = addr_el.text.strip() if addr_el else ""
        payload["address_raw"] = addr_text
        district = _district_from_text(addr_text) or _district_from_text(title)
        if district is None:
            log.info("591 %s: skip non-Taipei (addr=%r)", listing_id, addr_text)
            return None
        road = _road_from_address(addr_text, district)

        # Image: og:image meta or first listing image
        img_el = page.ele("css:meta[property='og:image']", timeout=1)
        image_url = img_el.attr("content") if img_el else None

        return RawListing(
            source="591",
            source_id=listing_id,
            url=url,
            title=title or f"591物件{listing_id}",
            price=price,
            rooms=rooms,
            bathrooms=bathrooms,
            district=district,
            road=road,
            has_elevator=True,  # filtered upstream via other=lift
            image_url=image_url,
            posted_at=datetime.now(timezone.utc),  # 591 doesn't expose exact post time easily
            scraped_payload=payload,
        )


def _parse_price(text: str) -> int | None:
    if not text:
        return None
    match = _PRICE_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _first_int(pattern: re.Pattern[str], text: str) -> int | None:
    match = pattern.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _district_from_text(text: str) -> str | None:
    """Return the first Taipei district found in text, or None."""
    if not text:
        return None
    for d in TAIPEI_DISTRICTS:
        if d in text:
            return d
    return None


def _road_from_address(addr: str, district: str) -> str | None:
    """Best-effort extraction of road segment from address."""
    if not addr or not district:
        return None
    idx = addr.find(district)
    if idx < 0:
        return None
    tail = addr[idx + len(district):]
    # Strip leading separators, keep first road token
    tail = tail.strip().lstrip("，,. ")
    # Stop at first digit (street number) or whitespace
    road = re.split(r"[\d\s號巷弄]", tail, maxsplit=1)[0].strip()
    return road or None
