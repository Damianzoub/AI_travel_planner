# Researcher Agent

Intelligence gathering. Knows everything about the destination. Knows nothing
about itinerary structure or prices.

---

## Single responsibility

Given a destination, travel dates, and a set of interests, produce a rich
`DestinationResearch` object with place candidates, weather, and travel logistics.

---

## What it reads from state

```python
state["task_plan"]["researcher_task"]  # ResearcherTask from the orchestrator
```

## What it writes to state

```python
state["destination_research"]  # DestinationResearch object
```

---

## Tools

| Tool | API | What it does |
|------|-----|--------------|
| `WebSearchTool` | Tavily | Searches for destination info, local tips, places |
| `WeatherTool` | OpenWeatherMap | 5-day forecast for travel dates |
| `WebFetchTool` | HTTP | Reads a specific URL in full (for travel blog deep dives) |

---

## Search strategy

The researcher runs multiple searches to cover different angles:

```python
queries = [
    f"best {interests[0]} {destination} locals recommendation 2025",
    f"hidden gems {destination} avoid tourist traps",
    f"best neighbourhoods stay {destination} {travel_style}",
    f"visa requirements {destination} {passport_country} citizens",
    f"travel tips {destination} {months_of_travel}"
]
```

It then synthesises the results — it does not dump raw search output into the state.
The output is a curated list of 10-15 place candidates with a quality bar:
only places mentioned by at least two independent sources are included.

---

## Output schema

```python
class DestinationResearch(BaseModel):
    destination_summary: str          # 2-3 sentence overview
    best_areas: list[Area]
    place_candidates: list[PlaceCandidate]
    weather_summary: WeatherSummary
    visa_notes: str
    travel_advisories: list[str]
    search_sources: list[str]         # URLs used — important for credibility

class Area(BaseModel):
    name: str
    description: str
    best_for: list[str]               # ["street food", "temples", "shopping"]

class PlaceCandidate(BaseModel):
    name: str
    type: str                         # "restaurant" | "attraction" | "market" | "experience"
    area: str
    description: str
    why_recommended: str
    estimated_cost_eur: float | None
    source_mentions: int              # how many sources mentioned this place

class WeatherSummary(BaseModel):
    forecast: list[DayForecast]
    packing_tips: list[str]
    weather_risks: list[str]          # e.g. "typhoon season, check forecasts daily"
```

---

## Caching opportunity

The researcher's output is the best candidate for caching in this system.
If two users plan trips to Tokyo in September within the same week, the
destination research is largely the same. A simple cache keyed on
`(destination, month)` with a 48-hour TTL saves API credits and latency.

This is not implemented in Phase 1 but is worth noting in the architecture docs.