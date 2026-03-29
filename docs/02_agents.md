# 02 — Agents

This document explains what each agent does, why it exists as a separate agent,
what tools it has access to, and what it outputs.

---

## Agent design principles

Before reading about each agent, understand the rules they all follow:

1. **Each agent has one job.** A researcher does not plan. A planner does not book.
   Single responsibility makes each agent testable in isolation.

2. **Every agent takes structured input and returns structured output.**
   No agent returns free-form text. Every output is a Pydantic model.

3. **Agents do not call each other directly.** They communicate only through
   the shared LangGraph state. The orchestrator is the only agent that sees
   the full picture.

4. **Prompts are versioned.** Every agent has a `prompts/` folder. When you
   change a prompt, you create a new version. This lets you A/B test and roll back.

---

## The Orchestrator

**File:** `agents/orchestrator/`
**Role:** Supervisor. The only agent that sees the full state.

### What it does

The orchestrator is the first agent to run and potentially runs multiple times
(once per revision loop). It does four things:

1. **Parses user intent** — extracts destination, dates, budget, interests, constraints
2. **Enriches with memory** — queries ChromaDB for user preferences and past trips
3. **Creates a TaskPlan** — a structured JSON that tells each agent exactly what to do
4. **Resolves revision feedback** — if the critic sends the plan back, the orchestrator
   reads the critique and adjusts the task plan before re-delegating

### What it does NOT do

It does not search the web, build itineraries, or fetch prices. It is a planner, not
a doer. Its only tools are the memory query tools.

### Output

```python
class TaskPlan(BaseModel):
    destination: str
    dates: DateRange
    budget_eur: float
    travel_style: str
    researcher_task: ResearcherTask
    planner_task: PlannerTask
    booker_task: BookerTask
    constraints: list[str]
    revision_notes: str | None  # filled on revision loops
```

### Why it exists as a separate agent

Without an orchestrator, you'd need to put all the coordination logic into a single
prompt, which becomes unmaintainably long. The orchestrator also lets you swap out
specialist agents (e.g. replace the booker with a different one) without touching
the planning logic.

---

## The Researcher

**File:** `agents/researcher/`
**Role:** Intelligence gathering. Knows nothing about itinerary structure.

### What it does

Takes the `ResearcherTask` from the task plan and produces a `DestinationResearch`
object. Specifically:

- Searches for top neighbourhoods, attractions, and local tips for the destination
- Fetches current weather for the travel dates
- Checks visa requirements based on user's passport (if stored in profile)
- Searches for any travel advisories or current events worth knowing
- Finds 10-15 place candidates (restaurants, attractions, experiences) that match
  the user's stated interests

### Tools it uses

- **Tavily search** — open-ended web queries ("best street food Tokyo Shibuya 2025")
- **Weather API** (OpenWeatherMap free tier) — 5-day forecast for travel dates
- **Web fetch** — reads specific travel blog posts or tourism pages in full

### Output

```python
class DestinationResearch(BaseModel):
    destination_summary: str
    best_areas: list[Area]
    place_candidates: list[PlaceCandidate]  # 10-15 places with name, type, area, notes
    weather_summary: WeatherSummary
    visa_notes: str
    travel_advisories: list[str]
    search_sources: list[str]  # URLs used — important for trust
```

### Why it exists as a separate agent

Destination research is open-ended. It requires multiple web searches with
different queries, reading long pages, and synthesising information. This takes
many LLM calls and several seconds. Isolating it lets you cache the results
(same destination, same month → reuse research) and test it independently.

---

## The Planner

**File:** `agents/planner/`
**Role:** Builds the day-by-day itinerary. The creative engine.

### What it does

Takes the `PlannerTask` from the task plan and the `DestinationResearch` from the
researcher, and produces a structured itinerary.

- Selects places from the researcher's candidates based on the user's travel style
- Clusters places by area to minimise travel time between them
- Assigns places to days, morning/afternoon/evening slots
- Queries Google Maps Directions API to calculate realistic transit times
- Optionally uses vision: sends Google Places photos to Claude to validate
  that a place actually looks like what was described

### Tools it uses

- **Google Maps Directions API** — transit time between two places
- **Google Maps Places API** — place details, opening hours, photos
- **Claude vision** — send a place photo, ask "does this look like a good
  street food spot for a solo traveller?" Returns a simple yes/no + reason

### Output

```python
class Itinerary(BaseModel):
    days: list[ItineraryDay]
    total_estimated_activity_cost_eur: float
    notes: str

class ItineraryDay(BaseModel):
    day_number: int
    date: str
    theme: str  # e.g. "Shibuya & Harajuku"
    slots: list[ItinerarySlot]
    transit_notes: str

class ItinerarySlot(BaseModel):
    time: str           # "09:00"
    duration_minutes: int
    place_name: str
    place_type: str     # "restaurant" | "attraction" | "transport" | "rest"
    area: str
    description: str
    estimated_cost_eur: float
    maps_url: str
    vision_validated: bool
```

### The vision validation step

This is the multimodal feature. For every restaurant in the itinerary, the planner:

1. Fetches the top 3 photos from Google Places API
2. Sends them to Claude with the prompt:
   "The user wants street food, affordable, local atmosphere. Do these photos
   match? Answer yes/no and give one sentence of reasoning."
3. If the answer is no, the planner swaps the place for the next candidate

This is a small but demonstrable use of multi-modal reasoning in a real workflow.

---

## The Booker

**File:** `agents/booker/`
**Role:** Fetches real prices. Lives in the real world.

### What it does

Takes the destination, dates, and budget from the task plan and finds real options:

- Queries Amadeus API for round-trip flight options (cheapest + recommended)
- Queries Amadeus Hotel Search for available hotels near the city centre
  filtered by star rating and price per night
- Calculates a total estimated cost (flights + hotel + activity budget from planner)
- Flags if the total exceeds the user's budget

### Tools it uses

- **Amadeus Flight Offers API** (free tier) — real flight prices
- **Amadeus Hotel List + Hotel Offers APIs** — real hotel availability and prices

### Output

```python
class BookingOptions(BaseModel):
    flights: list[FlightOption]
    hotels: list[HotelOption]
    total_estimated_cost_eur: float
    within_budget: bool
    budget_breakdown: BudgetBreakdown

class FlightOption(BaseModel):
    airline: str
    outbound: FlightLeg
    return_flight: FlightLeg
    price_eur: float
    booking_url: str | None

class HotelOption(BaseModel):
    name: str
    stars: int
    area: str
    price_per_night_eur: float
    total_price_eur: float
    amenities: list[str]
    booking_url: str | None
```

### Important note on real APIs

The Amadeus free tier ("test environment") returns real-looking data for a limited
set of routes. It is enough for a portfolio project. For production, you would
switch to their production credentials. Document this clearly in the project.

---

## The Critic

**File:** `agents/critic/`
**Role:** Quality control. The only agent that can reject a plan.

### What it does

Receives the full assembled plan (research + itinerary + booking options) and scores
it across five dimensions, each 0-10:

1. **Budget fit** — does the total cost fit within the stated budget?
2. **Pace** — is the day packed with too many or too few activities?
3. **Preference alignment** — do the places match the user's stated interests?
4. **Practicality** — are opening hours respected? Is transit time realistic?
5. **Diversity** — is there a good mix of experiences across the days?

### Decision logic

```
total_score = weighted average of the five dimensions

if total_score >= 7.0:
    return { approved: true, final_plan: assembled_plan }

if total_score < 7.0 and revision_count < 3:
    return {
        approved: false,
        critique: { scores, specific_issues, suggested_fixes },
        revision_count: revision_count + 1
    }

if revision_count >= 3:
    return { approved: true, final_plan: best_seen_plan, warnings: [...] }
```

The third rule (force-approve after 3 revisions) prevents infinite loops.

### Why this agent matters for your CV

Most AI projects deliver the first thing the LLM produces. The critic-revisor loop
means TravelMind can detect its own failures and improve them. This is the pattern
that separates a demo from a production system. In an interview, you can say:
"The system evaluates its own output against explicit criteria and retries when
it doesn't meet the bar. The criteria are configurable."

### Output

```python
class Critique(BaseModel):
    approved: bool
    total_score: float
    dimension_scores: dict[str, float]
    issues: list[str]          # specific problems found
    suggested_fixes: list[str] # concrete instructions for the orchestrator
    warnings: list[str]        # soft concerns even if approved
```

---

## How agents communicate

Agents do not import or call each other. Communication flows like this:

```
Orchestrator writes TaskPlan → state["task_plan"]
Researcher reads state["task_plan"]["researcher_task"]
Researcher writes → state["destination_research"]
Planner reads state["destination_research"] + state["task_plan"]["planner_task"]
Planner writes → state["itinerary"]
Booker reads state["task_plan"]["booker_task"]
Booker writes → state["booking_options"]
Critic reads state["itinerary"] + state["booking_options"] + state["task_plan"]
Critic writes → state["critique"]
Orchestrator reads state["critique"] on revision loops
```

This indirection is intentional. It makes the data flow visible and auditable.

---

Next: read `docs/03-memory.md` to understand how the system remembers users.