# Grocery Agent

WhatsApp grocery-ordering prototype.

User sends a grocery list on WhatsApp. The app parses it with Claude, compares prices across the configured provider, replies with the cheapest option, then creates a Razorpay payment link after the user replies `YES`.

## Current Flow

1. User sends a grocery list on WhatsApp.
2. Twilio sends the webhook request to `/whatsapp`.
3. FastAPI app in `main.py` receives the message.
4. Claude parses the grocery list into structured items.
5. Price provider is selected with `PRICE_PROVIDER`.
6. Comparison engine calculates totals and cheapest provider.
7. WhatsApp receives the price comparison.
8. User replies `YES`.
9. Razorpay payment link is generated.
10. WhatsApp receives the payment link.

## Project Structure

```text
.
├── main.py                         # FastAPI app, Twilio webhook, session flow
├── agents/
│   ├── grocery_agent.py            # Parser + price checker orchestration
│   ├── parser_agent.py             # Claude grocery parser
│   ├── price_checker.py            # Provider lookup + comparison
│   ├── comparison_engine.py        # Totals, savings, WhatsApp reply text
│   ├── payment_agent.py            # Razorpay payment link creation
│   └── providers/
│       ├── base.py                 # Provider contracts
│       ├── factory.py              # PRICE_PROVIDER selection
│       ├── mock_provider.py        # In-memory mock provider
│       ├── mongo_provider.py       # MongoDB-backed mock price provider
│       └── quickcommerce_provider.py
├── data/
│   └── mock_prices.mongodb.json    # MongoDB seed data
├── scripts/
│   └── seed_mongo_prices.py        # Loads mock price data into MongoDB
├── tests/
│   └── test_regression.py          # Regression tests
├── test_claude.py                  # Claude API smoke test
├── requirements.txt
└── README.md
```

## Setup

```bash
cd /Users/yogeshsoni/Projects/Grocery-agents
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The command creates a local virtual environment, activates it, and installs the Python packages used by FastAPI, Claude, Twilio, Razorpay, MongoDB, and tests.

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token

RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

PRICE_PROVIDER=mock

MONGO_URI=mongodb://localhost:27017
MONGO_DB=grocery_agent
MONGO_COLLECTION=mock_prices

QUICKCOMMERCE_API_BASE_URL=https://api.quickcommerceapi.com
QUICKCOMMERCE_API_KEY=
QUICKCOMMERCE_LAT=
QUICKCOMMERCE_LON=
QUICKCOMMERCE_PINCODE=
QUICKCOMMERCE_PLATFORMS=BlinkIt,Zepto,Swiggy,BigBasket
QUICKCOMMERCE_TIMEOUT_SECONDS=10
```

Do not commit `.env`.

## Price Providers

Supported `PRICE_PROVIDER` values:

- `mock`: default provider. Uses in-memory prices from `agents/providers/mock_provider.py`.
- `mongo`: uses MongoDB collection seeded from `data/mock_prices.mongodb.json`.
- `quickcommerce`: calls the QuickCommerce API when API key and location are configured.

Unknown provider values fall back to `mock`.

## Run With Mock Provider

Use this for the fastest local demo.

```bash
source venv/bin/activate
PRICE_PROVIDER=mock uvicorn main:app --reload --port 8000
```

The command starts the FastAPI app on port `8000` and uses local in-memory prices.

Health check:

```bash
curl http://localhost:8000/
```

Expected response:

```json
{"message":"Grocery Agent is running!"}
```

## Run With Mongo Provider

Start MongoDB locally first.

Seed mock grocery prices:

```bash
source venv/bin/activate
python scripts/seed_mongo_prices.py
```

The seed command loads `data/mock_prices.mongodb.json` into `grocery_agent.mock_prices`.

Run the app:

```bash
PRICE_PROVIDER=mongo uvicorn main:app --reload --port 8000
```

Mongo defaults:

```text
MONGO_URI=mongodb://localhost:27017
MONGO_DB=grocery_agent
MONGO_COLLECTION=mock_prices
```

Mongo seed data includes:

```text
milk, eggs, bread, butter, rice, sugar, salt, cooking oil, onion, tomato,
paneer, atta, dal, curd, cheese, chicken
```

## Run With QuickCommerce Provider

Set the QuickCommerce environment variables first:

```env
PRICE_PROVIDER=quickcommerce
QUICKCOMMERCE_API_KEY=your_api_key
QUICKCOMMERCE_LAT=your_latitude
QUICKCOMMERCE_LON=your_longitude
```

Run the app:

```bash
source venv/bin/activate
PRICE_PROVIDER=quickcommerce uvicorn main:app --reload --port 8000
```

`quickcommerce_provider.py` calls `/v1/groupsearch` with `X-API-Key`. It does not scrape vendor websites or assume private Blinkit, Instamart, Zepto, or BigBasket APIs.

If required QuickCommerce config is missing, the provider returns unavailable quotes and does not call the API.

## Run WhatsApp Webhook

Start FastAPI:

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Start ngrok in another terminal:

```bash
ngrok http 8000
```

Configure the Twilio WhatsApp sandbox webhook:

```text
https://your-ngrok-url.ngrok-free.app/whatsapp
```

Webhook method:

```text
POST
```

## Test Happy Path

Send this to the Twilio WhatsApp sandbox:

```text
2 litre milk, dozen eggs, brown bread
```

Expected behavior:

1. Terminal logs incoming WhatsApp message.
2. Claude parses the grocery list.
3. WhatsApp receives price comparison.
4. Reply `YES`.
5. WhatsApp receives Razorpay payment link.

## Useful Commands

Run regression tests without calling Claude, Razorpay, Twilio, or QuickCommerce:

```bash
PRICE_PROVIDER=mock venv/bin/python -m unittest discover -s tests
```

Compile-check Python files:

```bash
venv/bin/python -m py_compile main.py agents/*.py agents/providers/*.py scripts/seed_mongo_prices.py tests/test_regression.py
```

Test provider behavior:

```bash
PRICE_PROVIDER=mock venv/bin/python -m agents.price_checker
PRICE_PROVIDER=mongo venv/bin/python -m agents.price_checker
PRICE_PROVIDER=quickcommerce venv/bin/python -m agents.price_checker
PRICE_PROVIDER=unknown venv/bin/python -m agents.price_checker
```

Test Claude separately:

```bash
venv/bin/python test_claude.py
```

Check latest commit:

```bash
git log -1 --oneline
```

## Runtime Notes

- `main.py` has a 10 second timeout around grocery processing.
- Claude, Twilio, and Razorpay calls run through `asyncio.to_thread(...)` so the FastAPI route does not block directly.
- If no total is found, the app sends a fallback message instead of creating a payment session.
- User confirmation sessions are stored in the in-memory `user_sessions` dictionary.
- `quickcommerce` isolates live network behavior in `agents/providers/quickcommerce_provider.py`.
