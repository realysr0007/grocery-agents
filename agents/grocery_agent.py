from agents.parser_agent import parse_grocery_message
from agents.price_checker import check_prices


def process_grocery_message(user_message):
    parsed_items = parse_grocery_message(user_message)
    return check_prices(parsed_items)


if __name__ == "__main__":
    test = "2 litre milk, dozen eggs and brown bread"
    result = process_grocery_message(test)
    print(result)