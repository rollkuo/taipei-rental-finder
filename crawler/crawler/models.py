"""Normalized listing model produced by sources, consumed by supabase_client."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawListing:
    """A rental listing extracted from any source, before DB upsert."""

    source: str                      # "591" | "591_manual" | ...
    source_id: str                   # Source-native ID (e.g., 591 listing ID)
    url: str
    title: str
    price: int                       # Monthly rent in NT$
    rooms: int                       # Bedroom count
    bathrooms: int                   # Bathroom count
    district: str                    # e.g., "信義區"
    road: str | None = None
    has_elevator: bool = True
    image_url: str | None = None
    posted_at: datetime | None = None
    scraped_payload: dict[str, Any] = field(default_factory=dict)

    def to_db_row(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "rooms": self.rooms,
            "bathrooms": self.bathrooms,
            "district": self.district,
            "road": self.road,
            "has_elevator": self.has_elevator,
            "image_url": self.image_url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "scraped_payload": self.scraped_payload,
        }
