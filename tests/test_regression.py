import os
import unittest
from unittest.mock import patch

from agents.comparison_engine import compare_provider_quotes
from agents.price_checker import check_prices
from agents.providers.base import ProviderQuote, VendorItemPrice
from agents.providers.factory import get_price_provider
from agents.providers.mock_provider import MockPriceProvider
from agents.providers.quickcommerce_provider import QuickCommerceProvider
from main import extract_confirmation_platform, extract_total


class ProviderRegressionTests(unittest.TestCase):
    def test_mock_is_default_provider(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = get_price_provider()

        self.assertIsInstance(provider, MockPriceProvider)

    def test_unknown_provider_falls_back_to_mock(self):
        with patch.dict(os.environ, {"PRICE_PROVIDER": "not-real"}, clear=True):
            provider = get_price_provider()

        self.assertIsInstance(provider, MockPriceProvider)

    def test_mock_price_check_does_not_call_quickcommerce(self):
        items = [
            {"name": "milk", "quantity": 2, "unit": "litre"},
            {"name": "eggs", "quantity": 1, "unit": "dozen"},
            {"name": "bread", "quantity": 1, "unit": "loaf"},
        ]

        with patch.dict(os.environ, {"PRICE_PROVIDER": "mock"}, clear=True):
            with patch(
                "agents.providers.quickcommerce_provider.requests.get",
                side_effect=AssertionError("QuickCommerce API must not be called"),
            ):
                result = check_prices(items)

        self.assertIn("Blinkit: ₹181", result)
        self.assertIn("Instamart: ₹185", result)
        self.assertIn("Reply YES to confirm order on Blinkit.", result)

    def test_quickcommerce_missing_config_returns_unavailable_without_request(self):
        with patch.dict(os.environ, {"PRICE_PROVIDER": "quickcommerce"}, clear=True):
            provider = QuickCommerceProvider()
            with patch(
                "agents.providers.quickcommerce_provider.requests.get",
                side_effect=AssertionError("QuickCommerce API must not be called"),
            ):
                quotes = provider.lookup_prices([{"name": "milk"}])

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].prices, [])
        self.assertIn("QUICKCOMMERCE_API_KEY", quotes[0].unavailable_reason)

    def test_quickcommerce_payload_maps_vendor_prices(self):
        provider = QuickCommerceProvider()
        payload = {
            "status": "success",
            "data": {
                "results": {
                    "BlinkIt": [
                        {
                            "name": "Amul Taaza Milk",
                            "offer_price": 28,
                            "available": True,
                            "platform": {"name": "BlinkIt"},
                        }
                    ],
                    "Swiggy": [
                        {
                            "name": "Milk",
                            "price": "30",
                            "available": True,
                            "platform": {"name": "Swiggy"},
                        }
                    ],
                    "Zepto": [],
                }
            },
        }

        quote = provider.quote_from_payload({"name": "milk"}, payload)
        prices = {price.vendor: price for price in quote.prices}

        self.assertEqual(prices["blinkit"].unit_price, 28)
        self.assertEqual(prices["instamart"].unit_price, 30)
        self.assertFalse(prices["zepto"].available)


class ComparisonRegressionTests(unittest.TestCase):
    def test_comparison_supports_multiple_vendors_and_unavailable_items(self):
        quotes = [
            ProviderQuote(
                item={"name": "milk", "quantity": 2},
                prices=[
                    VendorItemPrice("blinkit", "milk", 28),
                    VendorItemPrice("instamart", "milk", 30),
                    VendorItemPrice("zepto", "milk", 27),
                ],
            ),
            ProviderQuote(
                item={"name": "eggs", "quantity": 1},
                prices=[
                    VendorItemPrice("blinkit", "eggs", 80),
                    VendorItemPrice("instamart", "eggs", 75),
                    VendorItemPrice("zepto", "eggs", 0, available=False),
                ],
            ),
            ProviderQuote(item={"name": "paneer"}, prices=[]),
        ]

        result = compare_provider_quotes(quotes)

        self.assertIn("Blinkit: ₹136", result)
        self.assertIn("Instamart: ₹135", result)
        self.assertIn("Zepto: ₹54", result)
        self.assertIn("Instamart saves you ₹1!", result)
        self.assertIn("- paneer", result)

    def test_main_confirmation_helpers_parse_display_text(self):
        comparison = "\n".join(
            [
                "🛒 Price Comparison:",
                "",
                "Blinkit: ₹181",
                "",
                "Reply YES to confirm order on Blinkit.",
            ]
        )

        platform = extract_confirmation_platform(comparison)

        self.assertEqual(platform, "Blinkit")
        self.assertEqual(extract_total(comparison, platform), "181")

    def test_comparison_without_winner_does_not_ask_for_confirmation(self):
        result = compare_provider_quotes(
            [ProviderQuote(item={"name": "paneer"}, prices=[])]
        )

        self.assertIn("No provider prices found.", result)
        self.assertIn("No winning provider found.", result)
        self.assertNotIn("Reply YES", result)


if __name__ == "__main__":
    unittest.main()
