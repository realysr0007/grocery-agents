try:
    from .base import PriceProvider, ProviderQuote, VendorItemPrice
except ImportError:
    from base import PriceProvider, ProviderQuote, VendorItemPrice


MOCK_PRICES = {
    "milk": {"blinkit": 28, "instamart": 30},
    "eggs": {"blinkit": 80, "instamart": 75},
    "bread": {"blinkit": 45, "instamart": 50},
    "butter": {"blinkit": 55, "instamart": 52},
    "rice": {"blinkit": 120, "instamart": 115},
    "sugar": {"blinkit": 45, "instamart": 48},
    "salt": {"blinkit": 20, "instamart": 18},
    "oil": {"blinkit": 150, "instamart": 145},
    "onion": {"blinkit": 30, "instamart": 35},
    "tomato": {"blinkit": 40, "instamart": 38},
}


def match_mock_item_name(item_name):
    if item_name in MOCK_PRICES:
        return item_name

    for mock_item_name in MOCK_PRICES:
        if mock_item_name in item_name:
            return mock_item_name

    return None


class MockPriceProvider(PriceProvider):
    name = "mock"

    def lookup_prices(self, items):
        quotes = []

        for item in items:
            item_name = item.get("name") or item.get("item", "")
            item_name = item_name.lower().strip()
            matched_name = match_mock_item_name(item_name)
            vendor_prices = MOCK_PRICES.get(matched_name) if matched_name else None

            if not vendor_prices:
                quotes.append(
                    ProviderQuote(
                        item=item,
                        prices=[],
                        unavailable_reason="Item not found in mock price database",
                    )
                )
                continue

            prices = [
                VendorItemPrice(
                    vendor=vendor,
                    item_name=item_name,
                    matched_name=matched_name,
                    unit_price=unit_price,
                )
                for vendor, unit_price in vendor_prices.items()
            ]

            quotes.append(ProviderQuote(item=item, prices=prices))

        return quotes


if __name__ == "__main__":
    provider = MockPriceProvider()

    test_items = [
        {
            "name": "amul milk",
            "quantity": 2,
            "unit": "litre",
            "brand": "Amul",
            "raw_phrase": "2 litre Amul milk",
        },
        {
            "name": "eggs",
            "quantity": 1,
            "unit": "dozen",
            "brand": None,
            "raw_phrase": "dozen eggs",
        },
        {
            "name": "brown bread",
            "quantity": 1,
            "unit": "loaf",
            "brand": None,
            "raw_phrase": "brown bread",
        },
        {
            "name": "paneer",
            "quantity": 200,
            "unit": "g",
            "brand": None,
            "raw_phrase": "200g paneer",
        },
    ]

    quotes = provider.lookup_prices(test_items)

    for quote in quotes:
        print(f"\nItem: {quote.item}")

        if quote.unavailable_reason:
            print(f"Unavailable: {quote.unavailable_reason}")
            continue

        for price in quote.prices:
            print(
                f"- {price.vendor}: {price.currency} {price.unit_price} "
                f"for {price.matched_name}"
            )
