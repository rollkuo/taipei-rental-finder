"""Test the RawListing model serialization."""

from datetime import datetime, timezone

from crawler.models import RawListing


def test_to_db_row_full():
    posted = datetime(2026, 6, 9, 10, 30, tzinfo=timezone.utc)
    listing = RawListing(
        source="591",
        source_id="12345",
        url="https://rent.591.com.tw/12345.html",
        title="3房精緻電梯華廈",
        price=80000,
        rooms=3,
        bathrooms=2,
        district="信義區",
        road="忠孝東路五段",
        has_elevator=True,
        image_url="https://example.com/img.jpg",
        posted_at=posted,
        scraped_payload={"raw": True},
    )
    row = listing.to_db_row()
    assert row["source"] == "591"
    assert row["source_id"] == "12345"
    assert row["price"] == 80000
    assert row["rooms"] == 3
    assert row["bathrooms"] == 2
    assert row["district"] == "信義區"
    assert row["posted_at"] == posted.isoformat()
    assert row["scraped_payload"] == {"raw": True}


def test_to_db_row_minimal():
    listing = RawListing(
        source="591_manual",
        source_id="99999",
        url="https://rent.591.com.tw/99999.html",
        title="t",
        price=50000,
        rooms=3,
        bathrooms=2,
        district="大安區",
    )
    row = listing.to_db_row()
    assert row["road"] is None
    assert row["posted_at"] is None
    assert row["image_url"] is None
    assert row["scraped_payload"] == {}
