# Grocery Agent

Agentic grocery ordering system that accepts a grocery list on WhatsApp, parses it with Claude, compares provider prices deterministically in Python, and sends a Razorpay payment link after user confirmation.

The current default price provider is a mock provider. The project also includes an isolated QuickCommerce aggregator provider that can be enabled with environment variables without changing the WhatsApp, confirmation, or payment flow.

## Flow

1. User sends a grocery list on WhatsApp.
2. Twilio forwards the WhatsApp webhook to an ngrok URL.
3. ngrok forwards the request to the local FastAPI app in `main.py`.
4. `main.py` calls `agents/grocery_agent.py`.
5. Claude parses the grocery list into structured JSON.
6. `agents/price_checker.py` selects a price provider through `agents/providers/factory.py`.
7. The selected provider returns provider quotes.
8. `agents/comparison_engine.py` calculates totals and savings deterministically.
9. `main.py` sends the price comparison back to the user on WhatsApp.
10. User replies `YES`.
11. `main.py` reads the saved session and calls `agents/payment_agent.py`.
12. Razorpay creates a payment link.
13. The payment link is sent back to the user on WhatsApp.

## Project Structure

```text
.
├── main.py                    # FastAPI webhook, session handling, Twilio replies
├── agents/
│   ├── grocery_agent.py       # Coordinates parsing and price checking
│   ├── payment_agent.py       # Razorpay payment link creation
│   ├── parser_agent.py
│   ├── price_checker.py       # Provider selection and comparison orchestration
│   ├── comparison_engine.py   # Deterministic totals, savings, and formatting
│   └── providers/
│       ├── base.py            # ProviderQuote and VendorItemPrice contracts
│       ├── factory.py         # PRICE_PROVIDER selection
│       ├── mock_provider.py   # Default local demo price provider
│       └── quickcommerce_provider.py
├── requirements.txt
└── test_claude.py             # Claude API smoke test
```

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
PRICE_PROVIDER=mock
QUICKCOMMERCE_API_BASE_URL=
QUICKCOMMERCE_API_KEY=
QUICKCOMMERCE_LAT=
QUICKCOMMERCE_LON=
QUICKCOMMERCE_PINCODE=
QUICKCOMMERCE_PLATFORMS=BlinkIt,Zepto,Swiggy,BigBasket
QUICKCOMMERCE_TIMEOUT_SECONDS=10
```

Do not commit `.env`.

`PRICE_PROVIDER` defaults to `mock`, so the app works without setting any new provider variables. Supported values:

- `mock`: uses local demo prices.
- `quickcommerce`: calls the documented QuickCommerce aggregator API when `QUICKCOMMERCE_API_KEY`, `QUICKCOMMERCE_LAT`, and `QUICKCOMMERCE_LON` are configured.

Unknown values fall back to the mock provider with a clear console message.

## Price Provider Architecture

The price provider layer is the extension point for real-time grocery pricing:

```text
main.py
-> agents/grocery_agent.py
-> agents/parser_agent.py
-> agents/price_checker.py
-> agents/providers/factory.py
-> agents/providers/mock_provider.py OR agents/providers/quickcommerce_provider.py
-> agents/comparison_engine.py
```

`QuickCommerceProvider` is intentionally conservative. It does not scrape websites and does not assume private Blinkit, Instamart, Zepto, or other undocumented API formats. All live QuickCommerce network behavior is isolated in `agents/providers/quickcommerce_provider.py`.

The provider:

- calls `/v1/groupsearch` with `X-API-Key`
- searches one parsed grocery item at a time
- maps returned platform data into `VendorItemPrice`
- normalizes vendor names before data reaches `comparison_engine.py`
- returns unavailable quotes when required config is missing, the API fails, an item is unavailable, or the response shape is unexpected

## Local Setup

```bash
cd /Users/yogeshsoni/Projects/Grocery-agents
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install razorpay
```

`razorpay` is imported by `agents/payment_agent.py`. If it is not already installed in your environment, install it with the command above.

## Run The App

Start FastAPI:

```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Start ngrok in another terminal:

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL from ngrok and configure Twilio WhatsApp sandbox webhook:

```text
https://your-ngrok-url.ngrok-free.app/whatsapp
```

Use `POST` as the webhook method.

## Test The Happy Path

Send a WhatsApp message to the Twilio sandbox:

```text
2 litre milk, dozen eggs, brown bread
```

Expected behavior:

1. Terminal logs show the incoming Twilio message.
2. Terminal logs show `Calling process_grocery_message...`.
3. WhatsApp receives a price comparison.
4. Reply `YES`.
5. WhatsApp receives a Razorpay payment link.

## Useful Commands

Check the app starts syntactically:

```bash
venv/bin/python -m py_compile main.py agents/grocery_agent.py agents/parser_agent.py agents/price_checker.py agents/comparison_engine.py agents/providers/base.py agents/providers/mock_provider.py agents/providers/factory.py agents/providers/quickcommerce_provider.py agents/payment_agent.py
```

Run the local regression suite without calling Claude, Razorpay, Twilio, or QuickCommerce:

```bash
PRICE_PROVIDER=mock venv/bin/python -m unittest discover -s tests
```

Verify provider behavior:

```bash
venv/bin/python -m agents.price_checker
unset PRICE_PROVIDER
venv/bin/python -m agents.price_checker
PRICE_PROVIDER=mock venv/bin/python -m agents.price_checker
PRICE_PROVIDER=unknown venv/bin/python -m agents.price_checker
PRICE_PROVIDER=quickcommerce venv/bin/python -m agents.price_checker
```

Only run the `PRICE_PROVIDER=quickcommerce` command when you intentionally want to exercise the real QuickCommerce provider. With missing QuickCommerce config it returns unavailable quotes and does not call the API.

Test Claude separately:

```bash
venv/bin/python test_claude.py
```

See the latest Git commit:

```bash
git log -1 --oneline
```

## Debugging Notes

### WhatsApp receives no reply after `Has alnum: True`

The May 2026 fix in `main.py` addressed this by:

- Removing an accidental early `return` that caused non-empty messages to exit before grocery processing.
- Running blocking Claude and Razorpay calls with `asyncio.to_thread(...)`.
- Adding a 10 second timeout around `process_grocery_message(...)`.
- Initializing `reply` before branching so it is always defined.
- Wrapping grocery processing in `try/except`.
- Sending a fallback WhatsApp reply when Claude, parsing, payment, or Twilio fails.
- Parsing totals with regex instead of `line.split("₹")[-1]`.

If this issue returns, watch for these log lines:

```text
Message from: ...
Message content: ...
Has alnum: True
Calling process_grocery_message...
process_grocery_message took: ...
Reply sent to ...
```

If `Calling process_grocery_message...` appears but no comparison is returned, check:

- `ANTHROPIC_API_KEY` is present and valid.
- The Claude model name in `agents/parser_agent.py` is available.
- The request finishes before `GROCERY_AGENT_TIMEOUT_SECONDS`.
- Network access is working from the machine running FastAPI.

If payment link generation fails after replying `YES`, check:

- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
- The `razorpay` Python package is installed.
- The `total` saved in `user_sessions` is numeric.

## Current Mock Price Database

The mock prices are stored in `agents/providers/mock_provider.py`:

```text
milk, eggs, bread, butter, rice, sugar, salt, oil, onion, tomato
```

Items outside this list may be returned as unavailable by the mock provider.
