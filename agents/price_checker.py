from agents.comparison_engine import compare_provider_quotes
from agents.providers.factory import get_price_provider


def check_prices(parsed_message):
    provider = get_price_provider()
    quotes = provider.lookup_prices(parsed_message)
    return compare_provider_quotes(quotes)


if __name__ == "__main__":
    test_parsed = [
        {
            "name": "milk",
            "quantity": 2,
            "unit": "litre",
            "brand": None,
            "raw_phrase": "2 litre milk",
        },
        {
            "name": "eggs",
            "quantity": 1,
            "unit": "dozen",
            "brand": None,
            "raw_phrase": "dozen eggs",
        },
        {
            "name": "bread",
            "quantity": 1,
            "unit": "loaf",
            "brand": None,
            "raw_phrase": "brown bread",
        },
    ]

    result = check_prices(test_parsed)
    print(result)
