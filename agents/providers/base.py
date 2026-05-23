from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VendorItemPrice:
    vendor: str
    item_name: str
    unit_price: float
    currency: str = "INR"
    available: bool = True
    matched_name: str | None = None


@dataclass(frozen=True)
class ProviderQuote:
    item: dict[str, Any]
    prices: list[VendorItemPrice] = field(default_factory=list)
    unavailable_reason: str | None = None


class PriceProvider(ABC):
    name: str

    @abstractmethod
    def lookup_prices(self, items: list[dict[str, Any]]) -> list[ProviderQuote]:
        """Return vendor prices for parsed grocery items."""