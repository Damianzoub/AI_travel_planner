# 04 — Tools & External APIs

Every external service TravelMind uses, why it was chosen, how to get credentials,
and what the wrapper looks like.

---

## Tool design principle

All external API calls are wrapped in a `BaseTool` class that:

1. Handles retries (3 attempts with exponential backoff)
2. Returns a typed result or a structured error (never raises unhandled exceptions)
3. Logs every call with latency for observability
4. Can be mocked in tests with a single flag

```python
class ToolResult(BaseModel):
    success: bool
    data: dict | None
    error: str | None
    latency_ms: int
```

Agents never call APIs directly. They call tool wrappers. This means you can swap
Amadeus for Skyscanner by changing one file.

---

## Tavily — Web Search

**Used by:** Researcher agent
**Purpose:** Open-ended web search for destination information

### Why Tavily instead of Google Search API?

Tavily is purpose-built for AI agents. It returns clean, structured search results
optimised for LLM consumption — no HTML noise, no ads, just relevant content.
The free tier gives 1,000 searches/month which is plenty for development.

### Setup

```bash
pip install tavily-python
export TAVILY_API_KEY="tvly-..."
```

### Example call

```python
from tavily import TavilyClient

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

result = client.search(
    query="best street food neighbourhoods Tokyo for solo traveller 2025",
    search_depth="advanced",   # more thorough, uses more credits
    max_results=5,
    include_answer=True        # Tavily gives a synthesised answer + sources
)
# result["answer"] → synthesised paragraph
# result["results"] → list of {title, url, content, score}
```

### Free tier limits

1,000 requests/month. Advanced searches cost 2 credits each.
Budget: ~500 advanced searches/month. More than enough for development.

---

## Amadeus — Flights & Hotels

**Used by:** Booker agent
**Purpose:** Real flight prices and hotel availability

### Why Amadeus?

It has the best free tier for developers. The test environment returns realistic
data for many routes and is free with no credit card required.

### Setup

```bash
pip install amadeus
```

Register at: https://developers.amadeus.com
Create an app → get `API Key` and `API Secret`.

```python
from amadeus import Client, ResponseError

amadeus = Client(
    client_id=os.environ["AMADEUS_API_KEY"],
    client_secret=os.environ["AMADEUS_API_SECRET"]
    # hostname="test" by default — change to "production" for live data
)
```

### Flight search

```python
response = amadeus.shopping.flight_offers_search.get(
    originLocationCode="ATH",
    destinationLocationCode="TYO",
    departureDate="2025-09-10",
    returnDate="2025-09-15",
    adults=1,
    currencyCode="EUR",
    max=5
)
flights = response.data  # list of flight offer objects
```

### Hotel search

```python
# Step 1: get hotel IDs for a city
hotels_response = amadeus.reference_data.locations.hotels.by_city.get(
    cityCode="TYO"
)

# Step 2: get prices for those hotels
offers_response = amadeus.shopping.hotel_offers_search.get(
    hotelIds=hotel_ids[:10],  # max 10 per call on free tier
    checkInDate="2025-09-10",
    checkOutDate="2025-09-15",
    adults=1,
    currencyCode="EUR"
)
```

### Free tier limits

Test environment only. Rate limit: 1 request/100ms. No monthly cap.
Production requires a paid plan.

### Important note to document in your project

The Amadeus test environment returns real-looking but synthetic data for a curated
set of routes. Document this clearly — it shows engineering honesty and
awareness of the difference between demo and production systems.

---

## Google Maps — Routing & Places

**Used by:** Planner agent
**Purpose:** Transit time between places, place details, place photos

### Setup

Get a key at: https://console.cloud.google.com
Enable: Maps JavaScript API, Directions API, Places API (New)

```bash
export GOOGLE_MAPS_API_KEY="AIza..."
pip install googlemaps
```

### Transit time between two places

```python
import googlemaps
from datetime import datetime

gmaps = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])

directions = gmaps.directions(
    origin="Senso-ji Temple, Tokyo",
    destination="Shibuya Crossing, Tokyo",
    mode="transit",
    departure_time=datetime.now()
)
# directions[0]["legs"][0]["duration"]["value"] → seconds
```

### Place details + photos

```python
# Search for a place
places_result = gmaps.places(
    query="Ichiran Ramen Shibuya Tokyo",
    fields=["place_id", "name", "rating", "opening_hours", "photos"]
)

place_id = places_result["results"][0]["place_id"]

# Get photo reference
photo_ref = places_result["results"][0]["photos"][0]["photo_reference"]

# Build photo URL (returns a JPEG)
photo_url = (
    f"https://maps.googleapis.com/maps/api/place/photo"
    f"?maxwidth=400&photo_reference={photo_ref}&key={API_KEY}"
)
```

### Free tier limits

$200/month free credit (renews monthly). Sufficient for development.
Directions API: $5 per 1,000 requests.
Places API: $17 per 1,000 requests (basic data).

---

## Claude API — LLM + Vision

**Used by:** All agents (LLM reasoning), Planner (vision validation)

### Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Basic agent call

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=AGENT_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_message}]
)
```

### Vision call (place photo validation)

```python
import base64, httpx

# Fetch the image as bytes
image_data = base64.standard_b64encode(
    httpx.get(photo_url).content
).decode("utf-8")

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }
            },
            {
                "type": "text",
                "text": (
                    "The user wants authentic street food with a local atmosphere, "
                    "affordable prices, no tourist traps. Does this place match? "
                    "Reply with JSON: {\"match\": true/false, \"reason\": \"one sentence\"}"
                )
            }
        ]
    }]
)
```

### Structured output (tool use)

To get reliable JSON from Claude, use tool use / function calling:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    tools=[{
        "name": "create_itinerary",
        "description": "Create a structured day-by-day travel itinerary",
        "input_schema": Itinerary.model_json_schema()  # Pydantic → JSON Schema
    }],
    tool_choice={"type": "tool", "name": "create_itinerary"},
    messages=[{"role": "user", "content": prompt}]
)

# Extract structured output
tool_use_block = response.content[0]
itinerary = Itinerary(**tool_use_block.input)
```

---

## OpenWeatherMap — Weather

**Used by:** Researcher agent
**Purpose:** 5-day forecast for travel dates

### Setup

Free tier, register at: https://openweathermap.org/api
```bash
export OPENWEATHER_API_KEY="..."
pip install pyowm
```

### Example call

```python
import httpx

response = httpx.get(
    "https://api.openweathermap.org/data/2.5/forecast",
    params={
        "q": "Tokyo,JP",
        "appid": os.environ["OPENWEATHER_API_KEY"],
        "units": "metric",
        "cnt": 5
    }
)
forecast = response.json()
```

Free tier: 60 calls/minute, 1,000,000 calls/month.

---

## Environment variables reference

Create a `.env` file at the project root. Never commit this file.

```bash
# .env (add to .gitignore)
ANTHROPIC_API_KEY=sk-ant-...
AMADEUS_API_KEY=...
AMADEUS_API_SECRET=...
GOOGLE_MAPS_API_KEY=AIza...
TAVILY_API_KEY=tvly-...
OPENWEATHER_API_KEY=...

# App config
DATABASE_URL=db_path
CHROMA_DB_PATH=chroma_database_path
ENVIRONMENT=development   # development | production
```

Load with `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

Next: read `docs/05-agentic-patterns.md` to understand what this project demonstrates.