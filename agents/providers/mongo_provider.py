import os

from pymongo import MongoClient

from agents.providers.base import PriceProvider, ProviderQuote, VendorItemPrice


class MongoPriceProvider(PriceProvider):
    name = "mongo"

    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "grocery_agent")
        collection_name = os.getenv("MONGO_COLLECTION", "mock_prices")

        self.client = MongoClient(mongo_uri)
        self.collection = self.client[db_name][collection_name]

    def lookup_prices(self, items):
        quotes = []

        for item in items:
            item_name = item.get("name") or item.get("item", "")
            item_name = item_name.lower().strip()

            result = self.collection.find_one(
                {
                    "$or": [
                        {"normalized_name": item_name},
                        {"aliases": item_name},
                    ]
                },
                {"_id": 0},
            )

            if not result:
                quotes.append(
                    ProviderQuote(
                        item=item,
                        prices=[],
                        unavailable_reason="Item not found in MongoDB mock price database",
                    )
                )
                continue

            matched_name = result.get("normalized_name", item_name)
            vendor_prices = result.get("prices", {})
            prices = [
                VendorItemPrice(
                    vendor=vendor,
                    item_name=item_name,
                    matched_name=matched_name,
                    unit_price=price_data["unit_price"],
                    currency=price_data.get("currency", "INR"),
                    available=price_data.get("available", True),
                )
                for vendor, price_data in vendor_prices.items()
            ]

            quotes.append(ProviderQuote(item=item, prices=prices))

        return quotes
