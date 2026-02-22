from unittest.mock import MagicMock, patch

from src.trackers.platforms.pchome import PChomeTracker

MOCK_SEARCH_RESPONSE = {
    "prods": [
        {
            "Id": "DYAQD6-A9009CMYB",
            "Name": "Sony WH-1000XM5 耳機",
            "Price": {"M": 6990, "P": 8490},
            "Pic": {"B": "path/to/img.jpg"},
        }
    ]
}

MOCK_PRODUCT_RESPONSE = {
    "Id": "DYAQD6-A9009CMYB",
    "Name": "Sony WH-1000XM5 耳機",
    "Price": {"M": 6990, "P": 8490},
    "Stock": True,
}

MOCK_FLASH_RESPONSE = [
    {
        "Id": "ABCD12-XYZ",
        "Name": "AirPods Pro 2",
        "Price": {"M": 6500, "P": 8490},
    }
]


def test_search_products():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_SEARCH_RESPONSE,
        )
        results = tracker.search_products("Sony 耳機")
    assert len(results) == 1
    assert results[0].platform == "pchome"
    assert results[0].price == 6990


def test_fetch_price():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_PRODUCT_RESPONSE,
        )
        snapshot = tracker.fetch_price("DYAQD6-A9009CMYB")
    assert snapshot is not None
    assert snapshot.price == 6990
    assert snapshot.in_stock is True


def test_fetch_flash_deals():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_FLASH_RESPONSE,
        )
        deals = tracker.fetch_flash_deals()
    assert len(deals) == 1
    assert deals[0].platform == "pchome"
    assert deals[0].sale_price == 6500
