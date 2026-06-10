"""Unit tests for source parsing helpers — no network calls."""

import re

import pytest

from crawler.sources._591 import (
    _LISTING_ID_RE,
    _district_from_text,
    _first_int,
    _parse_price,
    _road_from_address,
    _591Source,
)
from crawler.config import Filters


class TestParsePrice:
    @pytest.mark.parametrize("text,expected", [
        ("55,000 元/月", 55000),
        ("120000", 120000),
        ("$30,500", 30500),
        ("", None),
        ("免費", None),
        ("月租 N/A", None),
    ])
    def test_parse(self, text: str, expected: int | None):
        assert _parse_price(text) == expected


class TestExtractInt:
    def test_rooms(self):
        assert _first_int(re.compile(r"(\d+)房"), "3房2廳2衛") == 3
        assert _first_int(re.compile(r"(\d+)房"), "套房格局") is None

    def test_baths(self):
        assert _first_int(re.compile(r"(\d+)衛"), "3房2廳2衛") == 2


class TestDistrict:
    @pytest.mark.parametrize("text,expected", [
        ("台北市信義區忠孝東路", "信義區"),
        ("大安區仁愛路", "大安區"),
        ("台北市中山區民權東路", "中山區"),
        ("新北市板橋區", None),
        ("高雄市三民區", None),
        ("", None),
    ])
    def test_district(self, text: str, expected: str | None):
        assert _district_from_text(text) == expected


class TestRoadExtract:
    def test_basic(self):
        assert _road_from_address("台北市信義區忠孝東路五段", "信義區") == "忠孝東路五段"

    def test_with_number(self):
        # Should strip street numbers
        assert _road_from_address("台北市大安區仁愛路一段50號", "大安區").startswith("仁愛路")

    def test_no_match(self):
        assert _road_from_address("無效地址", "信義區") is None


class TestListingIdExtract:
    @pytest.mark.parametrize("url,expected", [
        ("https://rent.591.com.tw/12345.html", "12345"),
        ("https://rent.591.com.tw/67890", "67890"),
        ("https://rent.591.com.tw/foo/12345.html?ref=x", "12345"),
    ])
    def test_extract(self, url: str, expected: str):
        match = _LISTING_ID_RE.search(url)
        assert match is not None
        assert match.group(1) == expected


class TestSearchUrl:
    def test_posttime_sort_params(self):
        src = _591Source()
        f = Filters()
        url = src._build_search_url(f, "posttime")
        assert "region=1" in url
        assert "kind=1" in url
        assert "rentprice=,120000" in url
        assert "other=lift" in url
        assert "order=posttime" in url
        assert "orderType=desc" in url

    def test_price_sort_params(self):
        src = _591Source()
        f = Filters()
        url = src._build_search_url(f, "price")
        assert "region=1" in url
        assert "rentprice=,120000" in url
        assert "other=lift" in url
        assert "order=money" in url
        assert "orderType=asc" in url
