from agents.providers.base import ProviderQuote


VENDOR_DISPLAY_NAMES = {
    "blinkit": "Blinkit",
    "instamart": "Instamart",
    "zepto": "Zepto",
    "bigbasket": "BigBasket",
    "dmart": "DMart",
    "jiomart": "JioMart",
    "minutes": "Minutes",
}


def get_item_name(item):
    return (item.get("name") or item.get("item") or "unknown item").strip()


def get_quantity(item):
    try:
        quantity = float(item.get("quantity", 1))
    except (TypeError, ValueError):
        return 1

    return quantity if quantity > 0 else 1


def format_amount(amount):
    if float(amount).is_integer():
        return str(int(amount))
    return f"{amount:.2f}"


def display_vendor(vendor):
    return VENDOR_DISPLAY_NAMES.get(vendor, vendor.replace("_", " ").title())


def compare_provider_quotes(quotes: list[ProviderQuote]) -> str:
    vendor_totals = {}
    vendor_missing_items = set()
    item_breakdowns = []
    unavailable_items = []

    for quote in quotes:
        item = quote.item
        item_name = get_item_name(item)
        quantity = get_quantity(item)

        if not quote.prices:
            unavailable_items.append(item_name)
            continue

        available_prices = {
            price.vendor.lower(): price
            for price in quote.prices
            if price.available
        }

        all_vendors_for_item = sorted({price.vendor.lower() for price in quote.prices})

        if not available_prices:
            unavailable_items.append(item_name)
            item_breakdowns.append(
                {
                    "name": item_name,
                    "prices": {vendor: None for vendor in all_vendors_for_item},
                }
            )
            continue

        breakdown_prices = {}

        for vendor in all_vendors_for_item:
            vendor_totals.setdefault(vendor, 0.0)
            price = available_prices.get(vendor)

            if price is None:
                breakdown_prices[vendor] = None
                vendor_missing_items.add(vendor)
                continue

            subtotal = price.unit_price * quantity
            vendor_totals[vendor] += subtotal
            breakdown_prices[vendor] = subtotal

        item_breakdowns.append(
            {
                "name": item_name,
                "prices": breakdown_prices,
            }
        )

    eligible_totals = {
        vendor: total
        for vendor, total in vendor_totals.items()
        if total > 0 and vendor not in vendor_missing_items
    }

    if eligible_totals:
        winner = min(eligible_totals, key=eligible_totals.get)
        loser_totals = [
            total
            for vendor, total in eligible_totals.items()
            if vendor != winner
        ]
        savings = max(loser_totals) - eligible_totals[winner] if loser_totals else 0
    else:
        winner = None
        savings = 0

    lines = ["🛒 Price Comparison:", ""]

    for vendor, total in sorted(vendor_totals.items()):
        lines.append(f"{display_vendor(vendor)}: ₹{format_amount(total)}")

    if not vendor_totals:
        lines.append("No provider prices found.")

    lines.append("")

    if winner:
        winner_display = display_vendor(winner)
        lines.append(f"{winner_display} saves you ₹{format_amount(savings)}!")
    else:
        winner_display = "a provider"
        lines.append("No winning provider found.")

    lines.extend(["", "Item breakdown:"])

    for breakdown in item_breakdowns:
        item_name = breakdown["name"]
        vendor_parts = []

        for vendor, subtotal in sorted(breakdown["prices"].items()):
            amount_text = (
                f"₹{format_amount(subtotal)}"
                if subtotal is not None
                else "unavailable"
            )
            vendor_parts.append(f"{display_vendor(vendor)} {amount_text}")

        lines.append(f"- {item_name} - {' vs '.join(vendor_parts)}")

    if unavailable_items:
        lines.append("")
        lines.append("Unavailable:")
        for item_name in unavailable_items:
            lines.append(f"- {item_name}")

    if winner:
        lines.extend(["", f"Reply YES to confirm order on {winner_display}."])

    return "\n".join(lines)
