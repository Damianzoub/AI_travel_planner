# Orchestrator Agent

The supervisor. The only agent that sees the full trip state and understands the
user's goal. Runs first, and may run again on revision loops.

---

## Single responsibility

Create a `TaskPlan` — a structured set of instructions for each specialist agent —
and revise it if the critic sends the plan back.

---

## What it reads from state

```python
state["user_request"]       # raw user input
state["user_preferences"]   # from ChromaDB (injected by backend before graph starts)
state["past_trips"]         # from SQLite (injected by backend before graph starts)
state["critique"]           # only on revision loops (None on first run)
state["revision_count"]     # how many times we have looped
```

## What it writes to state

```python
state["task_plan"]  # TaskPlan object → tells each agent what to do
```

---

## Tools

The orchestrator has no external tools. It only reasons over the data it already has.

---

## Prompt strategy

The orchestrator's prompt does four things:

1. **Extract intent** — parse destination, dates, budget, interests from the user's
   natural language request (even if phrased informally)

2. **Integrate memory** — the prompt includes the retrieved preferences and past trips,
   with an explicit instruction: "Respect these preferences unless the user's current
   request overrides them explicitly."

3. **Create the TaskPlan** — each sub-task is a specific instruction for one agent.
   For example, the `PlannerTask` says "Build a 5-day itinerary for Tokyo. Max 3
   activities per day. User prefers street food and temples. Avoid Shibuya crossing
   (done it before)."

4. **Handle revision notes** — on second+ runs, the prompt includes the critic's
   specific feedback and says: "The previous plan was rejected for these reasons.
   Adjust the relevant task instructions to address each issue."

---

## Revision loop behaviour

On the first run: `state["critique"]` is `None`. Orchestrator creates the initial plan.

On revision runs: `state["critique"]` contains the critic's structured feedback:
```json
{
    "approved": false,
    "issues": ["Plan exceeds budget by €340", "Day 3 has 6 activities — too many"],
    "suggested_fixes": ["Swap 4-star hotel for 3-star", "Remove 2 activities from Day 3"]
}
```

The orchestrator reads these and adjusts only the relevant task instructions.
It does not re-run agents whose outputs were not criticised.

---

## Output schema

```python
class TaskPlan(BaseModel):
    destination: str
    destination_code: str       # IATA city code e.g. "TYO"
    dates: DateRange
    budget_eur: float
    travel_style: str
    interests: list[str]
    constraints: list[str]

    researcher_task: ResearcherTask
    planner_task: PlannerTask
    booker_task: BookerTask

    memory_context: str         # summary of what was retrieved from memory
    revision_notes: str | None  # populated on revision loops

class ResearcherTask(BaseModel):
    destination: str
    travel_dates: DateRange
    focus_areas: list[str]      # ["street food", "temples", "local markets"]
    avoid: list[str]            # ["tourist traps", "chain restaurants"]
    passport_country: str | None

class PlannerTask(BaseModel):
    destination: str
    num_days: int
    max_activities_per_day: int
    interests: list[str]
    travel_style: str
    avoid_places: list[str]     # from memory: places visited before

class BookerTask(BaseModel):
    origin_city: str            # where the user is flying from
    destination_code: str
    outbound_date: str
    return_date: str
    budget_flights_eur: float   # portion of budget for flights
    budget_hotel_per_night_eur: float
    adults: int
```

---

## Common failure mode

The orchestrator may misparse an informal user request ("something warm in October,
not too expensive, I like food a lot"). Ensure the system prompt includes examples
of informal requests mapped to structured task plans. A few-shot examples in the
prompt dramatically improve parsing reliability.