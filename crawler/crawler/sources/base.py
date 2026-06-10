"""Protocol every source adapter must implement."""

from typing import Iterator, Protocol

from ..config import Filters
from ..models import RawListing


class ListingSource(Protocol):
    name: str

    def fetch(self, filters: Filters) -> Iterator[RawListing]:
        """Yield listings matching filters. Filtering may be partial — main.py applies final filter."""
        ...
