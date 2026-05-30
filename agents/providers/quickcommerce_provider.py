import os
from urllib.parse import urljoin

import requests

from agents.providers.base import PriceProvider, ProviderQuote, VendorItemPrice


REQUIRED_ENV_VARS = (
    "QUICKCOMMERCE_API_KEY",
    "QUICKCOMMERCE_LAT",
    "QUICKCOMMERCE_LON",
)

DEFAULT_API_BASE_URL = "https://api.quickcommerceapi.com"
DEFAULT_PLATFORMS = "BlinkIt,Zepto,Swiggy,BigBasket"
REQUEST_TIMEOUT_SECONDS = 10

VENDOR_NAME_MAP = {
    "blinkit": "blinkit",
    "swiggy": "instamart",
    "swiggy instamart": "instamart",
    "zepto": "zepto",
    "bigbasket": "bigbasket",
    "dmart": "dmart",
    "jiomart": "jiomart",
    "minutes": "minutes",
}


class QuickCommerceProvider(PriceProvider):
    name = "quickcommerce"

    def __init__(self):
        self.api_base_url = (
            os.getenv("QUICKCOMMERCE_API_BASE_URL", DEFAULT_API_BASE_URL).strip()
            or DEFAULT_API_BASE_URL
        )
        self.api_key = os.getenv("QUICKCOMMERCE_API_KEY", "").strip()
        self.lat = os.getenv("QUICKCOMMERCE_LAT", "").strip()
        self.lon = os.getenv("QUICKCOMMERCE_LON", "").strip()
        self.pincode = os.getenv("QUICKCOMMERCE_PINCODE", "").strip()
        self.platforms = os.getenv(
            "QUICKCOMMERCE_PLATFORMS",
            DEFAULT_PLATFORMS,
        ).strip()

        try:
            self.timeout_seconds = float(
                os.getenv("QUICKCOMMERCE_TIMEOUT_SECONDS", REQUEST_TIMEOUT_SECONDS)
            )
        except ValueError:
            self.timeout_seconds = REQUEST_TIMEOUT_SECONDS

    def is_configured(self):
        return bool(self.api_key and self.lat and self.lon)

    def missing_config_reason(self):
        missing = [
            env_var
            for env_var, value in (
                ("QUICKCOMMERCE_API_KEY", self.api_key),
                ("QUICKCOMMERCE_LAT", self.lat),
                ("QUICKCOMMERCE_LON", self.lon),
            )
            if not value
        ]
        return f"QuickCommerce provider is not configured; set {', '.join(missing)}."

    def build_search_query(self, item):
        brand = (item.get("brand") or "").strip()
        item_name = (item.get("name") or item.get("item") or "").strip()
        return " ".join(part for part in (brand, item_name) if part).strip()

    def groupsearch_url(self):
        return urljoin(self.api_base_url.rstrip("/") + "/", "v1/groupsearch")

    def build_request_params(self, query):
        params = {
            "q": query,
            "lat": self.lat,
            "lon": self.lon,
            "platforms": self.platforms,
        }

        if self.pincode:
            params["pincode"] = self.pincode

        return params

    def request_groupsearch(self, query):
        response = requests.get(
            self.groupsearch_url(),
            headers={"X-API-Key": self.api_key},
            params=self.build_request_params(query),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def normalize_vendor_name(self, vendor_name):
        normalized = str(vendor_name or "").strip().lower()
        return VENDOR_NAME_MAP.get(normalized, normalized)

    def platform_name_from_product(self, fallback, product):
        platform = product.get("platform")

        if isinstance(platform, dict):
            return platform.get("name") or fallback

        if isinstance(platform, str):
            return platform

        return fallback

    def price_from_product(self, product):
        raw_price = product.get("offer_price", product.get("price"))

        if raw_price is None:
            return None

        try:
            return float(raw_price)
        except (TypeError, ValueError):
            return None

    def quote_from_payload(self, item, payload):
        if payload.get("status") != "success":
            return ProviderQuote(
                item=item,
                prices=[],
                unavailable_reason="QuickCommerce API returned an unsuccessful response.",
            )

        results = payload.get("data", {}).get("results")
        if not isinstance(results, dict):
            return ProviderQuote(
                item=item,
                prices=[],
                unavailable_reason="QuickCommerce API response did not include results.",
            )

        prices = []

        for platform_name, products in results.items():
            vendor = self.normalize_vendor_name(platform_name)

            if not isinstance(products, list) or not products:
                prices.append(
                    VendorItemPrice(
                        vendor=vendor,
                        item_name=str(item.get("name") or item.get("item") or ""),
                        unit_price=0,
                        available=False,
                    )
                )
                continue

            product = products[0]
            if not isinstance(product, dict):
                prices.append(
                    VendorItemPrice(
                        vendor=vendor,
                        item_name=str(item.get("name") or item.get("item") or ""),
                        unit_price=0,
                        available=False,
                    )
                )
                continue

            platform_display_name = self.platform_name_from_product(platform_name, product)
            unit_price = self.price_from_product(product)
            available = bool(product.get("available")) and unit_price is not None

            prices.append(
                VendorItemPrice(
                    vendor=self.normalize_vendor_name(platform_display_name),
                    item_name=str(item.get("name") or item.get("item") or ""),
                    matched_name=product.get("name"),
                    unit_price=unit_price or 0,
                    available=available,
                )
            )

        if not prices:
            return ProviderQuote(
                item=item,
                prices=[],
                unavailable_reason="Item was unavailable from QuickCommerce platforms.",
            )

        return ProviderQuote(item=item, prices=prices)

    def lookup_prices(self, items):
        if not self.is_configured():
            return [
                ProviderQuote(
                    item=item,
                    prices=[],
                    unavailable_reason=self.missing_config_reason(),
                )
                for item in items
            ]

        quotes = []

        for item in items:
            query = self.build_search_query(item)

            if not query:
                quotes.append(
                    ProviderQuote(
                        item=item,
                        prices=[],
                        unavailable_reason="Item did not include a searchable name.",
                    )
                )
                continue

            try:
                payload = self.request_groupsearch(query)
            except requests.RequestException as exc:
                quotes.append(
                    ProviderQuote(
                        item=item,
                        prices=[],
                        unavailable_reason=f"QuickCommerce API request failed: {exc}",
                    )
                )
                continue
            except ValueError:
                quotes.append(
                    ProviderQuote(
                        item=item,
                        prices=[],
                        unavailable_reason="QuickCommerce API returned invalid JSON.",
                    )
                )
                continue

            quotes.append(self.quote_from_payload(item, payload))

        return quotes