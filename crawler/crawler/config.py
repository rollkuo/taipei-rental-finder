"""Crawler configuration: filter criteria + env vars."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env.local from monorepo root (3 levels up: config.py → crawler/ → crawler-project/ → monorepo/)
_monorepo_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_monorepo_root / ".env.local")


@dataclass(frozen=True)
class Filters:
    """Hard rental criteria — not negotiable."""

    city_region_id: int = 1          # 591 region code: 1 = 台北市
    kind: int = 1                    # 591 kind: 1 = 整層住家 (whole apartment)
    min_rooms: int = 3               # 三房以上（硬條件）
    min_bathrooms: int = 2           # 兩衛以上
    max_price: int = 120_000         # 月租上限 NT$120,000
    require_elevator: bool = True


FILTERS = Filters()


def supabase_url() -> str:
    val = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    if not val:
        raise RuntimeError("SUPABASE_URL not set")
    return val


def supabase_service_key() -> str:
    val = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not val:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not set")
    return val


def discord_webhook_url() -> str | None:
    val = os.environ.get("DISCORD_WEBHOOK_URL")
    return val or None
