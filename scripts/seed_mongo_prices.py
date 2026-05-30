import json
from pathlib import Path

from pymongo import MongoClient


DATA_FILE = Path("data/mock_prices.mongodb.json")

client = MongoClient("mongodb://localhost:27017")
db = client["grocery_agent"]
collection = db["mock_prices"]


def main():
    with DATA_FILE.open("r") as file:
        prices = json.load(file)

    collection.delete_many({})
    collection.insert_many(prices)

    print(f"Seeded {len(prices)} mock price records into grocery_agent.mock_prices")


if __name__ == "__main__":
    main()