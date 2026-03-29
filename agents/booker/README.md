# Booker Agent

Lives in the real world. Fetches actual prices from external travel APIs.
Does no creative reasoning — just queries, parses, and returns.

---

## Single responsibility

Given origin, destination, dates, and budget targets, return real flight options
and hotel options with prices and booking links.

---

## What it reads from state

```python
state["task_plan"]["booker_task"]  # BookerTask from the orchestrator
```

## What it writes to state

```python
state["booking_options"]  # BookingOptions object
```

---

## Tools

| Tool | API | What it does |
|------|-----|--------------|
| `FlightSearchTool` | Amadeus Flight Offers API | Returns cheapest + recommended flights |
| `HotelSearchTool` | Amadeus Hotel APIs | Returns available hotels with prices |

---

## Flight search logic

```python
def search_flights(self, task: BookerTask) -> list[FlightOption]:
    # Search for up to 5 options
    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode=task.origin_city,
        destinationLocationCode=task.destination_code,
        departureDate=task.outbound_date,
        returnDate=task.return_date,
        adults=task.adults,
        currencyCode="EUR",
        max=5
    )

    options = []
    for offer in response.data:
        options.append(FlightOption(
            airline=offer["validatingAirlineCodes"][0],
            price_eur=float(offer["price"]["total"]),
            outbound=self._parse_leg(offer["itineraries"][0]),
            return_flight=self._parse_leg(offer["itineraries"][1]),
            booking_url=None  # Amadeus test env doesn't return booking URLs
        ))

    # Sort by price, return cheapest + one "value" pick
    return sorted(options, key=lambda x: x.price_eur)[:3]
```

---

## Budget awareness

The booker calculates a total and sets `within_budget`:

```python
cheapest_flight = min(flights, key=lambda f: f.price_eur)
cheapest_hotel = min(hotels, key=lambda h: h.total_price_eur)
activity_budget = state["itinerary"]["total_estimated_activity_cost_eur"]

total = cheapest_flight.price_eur + cheapest_hotel.total_price_eur + activity_budget
within_budget = total <= task.budget_eur
```

If `within_budget` is False, the critic will flag this as a budget failure and
the orchestrator will be told to reduce the hotel star rating or swap in cheaper
activities.

---

## Graceful degradation

If the Amadeus API is unavailable or returns no results:

```python
except ResponseError as e:
    return BookingOptions(
        flights=[],
        hotels=[],
        total_estimated_cost_eur=0,
        within_budget=None,       # unknown
        degraded=True,
        degraded_reason=str(e)
    )
```

The backend passes `degraded: true` to the frontend, which shows:
"Flight prices temporarily unavailable. Contact an agent or check Skyscanner."

The trip plan is still delivered — a degraded result is better than no result.

---

## Output schema

```python
class BookingOptions(BaseModel):
    flights: list[FlightOption]
    hotels: list[HotelOption]
    total_estimated_cost_eur: float
    within_budget: bool | None
    budget_breakdown: BudgetBreakdown
    degraded: bool = False
    degraded_reason: str | None = None

class FlightOption(BaseModel):
    airline: str
    outbound: FlightLeg
    return_flight: FlightLeg
    price_eur: float
    booking_url: str | None

class FlightLeg(BaseModel):
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    stops: int

class HotelOption(BaseModel):
    name: str
    stars: int
    area: str
    price_per_night_eur: float
    total_price_eur: float
    check_in: str
    check_out: str
    amenities: list[str]
    booking_url: str | None

class BudgetBreakdown(BaseModel):
    flights_eur: float
    hotel_eur: float
    activities_eur: float
    total_eur: float
    budget_eur: float
    surplus_or_deficit_eur: float   # positive = under budget, negative = over
```

---

## Note on Amadeus test environment

The free tier test environment covers a curated set of routes with real-looking
but not live data. Document this clearly in the project README. Switching to
production data requires a paid Amadeus account and the same code — just change
`hostname="production"` in the client initialisation.