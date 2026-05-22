import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def parse_grocery_message(user_message: str) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": f"""
You are a grocery list parser.

Extract grocery items from this WhatsApp message.

Return ONLY valid JSON. Do not include markdown, explanations, or extra text.

JSON schema:
{{
  "items": [
    {{
      "name": "string",
      "quantity": number,
      "unit": "string",
      "brand": "string or null",
      "raw_phrase": "string"
    }}
  ]
}}

Rules:
- name should be the normalized grocery item name, lowercase when possible.
- quantity should be numeric. Use 1 if quantity is implied.
- unit should be normalized, for example: kg, g, litre, ml, dozen, packet, loaf, piece.
- brand should be null unless the user clearly mentions a brand or preference.
- raw_phrase should preserve the original phrase for that item.
- If the user says "each", apply that quantity/unit to all affected items.
- If unit is missing, use "piece".

Message:
{user_message}
"""
            }
        ],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    print("Claude raw response:", repr(text))
    parsed = json.loads(text)
    return parsed.get("items", [])


if __name__ == "__main__":
    test_message = "2 litre Amul milk, dozen eggs and brown bread"
    print(json.dumps(parse_grocery_message(test_message), indent=2)) 