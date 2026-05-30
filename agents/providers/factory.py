import os

from agents.providers.mongo_provider import MongoPriceProvider

from agents.providers.mock_provider import MockPriceProvider
from agents.providers.quickcommerce_provider import QuickCommerceProvider


def get_price_provider():
    provider_name = os.getenv("PRICE_PROVIDER", "mock").strip().lower() or "mock"

    if provider_name == "mock":
        return MockPriceProvider()

    if provider_name == "mongo":
        return MongoPriceProvider()

    if provider_name == "quickcommerce":
        return QuickCommerceProvider()

    print(
        f"Unknown PRICE_PROVIDER={provider_name!r}; falling back to MockPriceProvider."
    )
    return MockPriceProvider()
