# Planner Agent

The creative engine. Builds the day-by-day itinerary from the researcher's
place candidates. The only agent that uses vision.

---

## Single responsibility

Given a `PlannerTask` and `DestinationResearch`, produce a structured `Itinerary`
with realistic day plans, transit-optimised routing, and vision-validated places.

---

## What it reads from state

```python
state["task_plan"]["planner_task"]   # PlannerTask from the orchestrator
state["destination_research"]         # DestinationResearch from the researcher
```

## What it writes to state

```python
state["itinerary"]  # Itinerary object
```

---

## Tools

| Tool | API | What it does |
|------|-----|--------------|
| `DirectionsTool` | Google Maps Directions API | Transit time between two places |
| `PlaceDetailsTool` | Google Maps Places API | Opening hours, photos for a place |
| `VisionValidationTool` | Claude API (vision) | Validates place photos against user prefs |

---

## Planning algorithm

The planner follows a deliberate sequence:

### Step 1 — Filter candidates

From the researcher's 10-15 candidates, filter down to 6-8 based on the `PlannerTask`
interests and `avoid_places` list. Score each candidate:

```
score = (interest_match * 0.5) + (source_mentions * 0.3) + (vision_score * 0.2)
```

### Step 2 — Cluster by area

Group the selected places by the area they're in (from the researcher's `Area` objects).
Places in the same area go on the same day to minimise travel. This is a simple
grouping, not a full TSP solver — good enough for 5-7 day trips.

### Step 3 — Build day structure

For each day, assign morning / afternoon / evening slots:
- Morning: one or two activities (lighter, no rush)
- Afternoon: main experience of the day (museum, market, long walk)
- Evening: dinner (restaurant candidate from the researcher)

Respect `max_activities_per_day` from the task plan.

### Step 4 — Validate with Maps API

For each day, call the Directions API to get transit times between consecutive places.
If transit time > 45 minutes between adjacent slots, flag the day for restructuring
and swap one place for a closer alternative.

### Step 5 — Vision validation

For every restaurant candidate in the itinerary:
1. Fetch top 3 photos via Google Places API
2. Send to Claude vision with the user's food preference context
3. If rejected (match: false), swap for the next-best restaurant candidate

This step runs last because it is the most API-credit-intensive.

---

## Output schema

```python
class Itinerary(BaseModel):
    days: list[ItineraryDay]
    total_estimated_activity_cost_eur: float
    itinerary_notes: str

class ItineraryDay(BaseModel):
    day_number: int
    date: str
    theme: str                        # e.g. "Asakusa & Ueno"
    slots: list[ItinerarySlot]
    transit_notes: str                # e.g. "Take subway Ginza line between stops"

class ItinerarySlot(BaseModel):
    time: str                         # "09:00"
    duration_minutes: int
    place_name: str
    place_type: str
    area: str
    description: str
    estimated_cost_eur: float
    maps_url: str
    google_place_id: str | None
    vision_validated: bool            # True if passed vision check
    opening_hours: str | None
```

---

## The vision validation step (multimodal)

This is the most distinctive part of the planner. Here is exactly what happens:

```python
def validate_place_with_vision(self, place: PlaceCandidate, user_prefs: str) -> bool:
    # 1. Get photo from Google Places
    photo_url = self.place_tool.get_photo_url(place.google_place_id)
    image_b64 = base64.b64encode(httpx.get(photo_url).content).decode()

    # 2. Ask Claude
    response = self.client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                {"type": "text", "text": f"User preferences: {user_prefs}\nDoes this place match? Reply only with JSON: {{\"match\": true/false, \"reason\": \"one sentence\"}}"}
            ]
        }]
    )

    result = json.loads(response.content[0].text)
    return result["match"]
```

In the itinerary output, `vision_validated: true` means the photo was seen and
approved. The UI can display a "verified" badge on those places.