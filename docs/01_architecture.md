# 01 — System Architecture

This document explains how all the pieces of TravelMind fit together.
Read this before touching any code.

---

## The big picture

TravelMind is built around a pattern called **supervisor-worker multi-agent orchestration**.
One central agent (the Orchestrator) receives the user's request, breaks it into
subtasks, and dispatches those subtasks to four specialist agents. Each specialist
has its own tools, its own prompt, and its own output schema.

The whole flow is implemented as a **state machine** using LangGraph. Every transition
between agents — and every decision to loop back or finish — is an explicit edge in
that graph. This makes the system debuggable: you can inspect exactly what state the
system was in when something went wrong.

---

## Full data flow

```
┌─────────────┐
│    User     │  "Plan 5 days in Tokyo, €1500, loves street food"
└──────┬──────┘
       │  HTTP POST /api/trip
       ▼
┌─────────────┐
│   FastAPI   │  validates input, creates trip session, streams response
│   Backend   │
└──────┬──────┘
       │  calls LangGraph graph
       ▼
┌──────────────────────────────────────────────────────┐
│                    LangGraph Graph                    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │             Orchestrator Agent               │    │
│  │  - reads user intent                        │    │
│  │  - queries memory for user preferences      │    │
│  │  - creates a TaskPlan (structured JSON)     │    │
│  │  - decides which agents to call and in      │    │
│  │    what order                               │    │
│  └───┬──────────┬──────────┬──────────┬────────┘    │
│      │          │          │          │              │
│      ▼          ▼          ▼          ▼              │
│  Researcher  Planner   Booker     Critic             │
│                                      │               │
│                           ┌──────────┘               │
│                           │ score < threshold?        │
│                           └──► back to Orchestrator   │
│                                                      │
└──────────────────────────────────────────────────────┘
       │
       │  final TripPlan (structured JSON)
       ▼
┌─────────────┐
│   FastAPI   │  formats response, saves to trip history
└──────┬──────┘
       │  Server-Sent Events (streaming) or JSON response
       ▼
┌─────────────┐
│  Next.js UI │  renders itinerary, map, prices
└─────────────┘
```

---

## Component responsibilities

### FastAPI backend

The backend is a thin layer. Its job is to:

- Accept HTTP requests from the frontend
- Validate the incoming data (Pydantic models)
- Start a LangGraph execution and stream its output
- Save results to the database
- Expose REST endpoints for trip history

The backend does **not** contain any agent logic. That all lives in the `agents/` layer.

### LangGraph graph

LangGraph lets you define agents as **nodes** and transitions as **edges** in a directed
graph. Each node receives the current **state** (a shared Python dict/TypedDict) and
returns updates to that state.

The state object for TravelMind looks like this:

```python
class TripState(TypedDict):
    # Input
    user_request: str
    user_id: str

    # Memory
    user_preferences: dict
    past_trips: list[dict]

    # Agent outputs (filled in as the graph runs)
    task_plan: dict          # set by orchestrator
    destination_research: dict  # set by researcher
    itinerary: dict          # set by planner
    booking_options: dict    # set by booker
    critique: dict           # set by critic

    # Control flow
    revision_count: int
    final_plan: dict
    status: str              # "in_progress" | "done" | "failed"
```

Every agent reads from this state and writes back to it. Nothing is passed between
agents directly — they all communicate through the shared state.

### Memory system

Memory sits outside the graph and is queried at specific points. There are three tiers:

1. **Session memory** — the LangGraph state itself. Lives for one trip planning session.
2. **Vector store** — ChromaDB. Stores embeddings of user preferences and past experiences.
   Queried by the orchestrator at the start of every session.
3. **Trip history** — SQLite/Postgres. Structured records of completed trips.
   Used to build the user's preference profile over time.

See `docs/03-memory.md` for the full memory design.

---

## Key design decisions

### Why LangGraph instead of CrewAI or AutoGen?

LangGraph gives you explicit control over the state machine. CrewAI and AutoGen are
higher-level and do more for you, but they also hide more from you. For a portfolio
project, you want to be able to explain every decision and debug every transition.
LangGraph forces you to think about state, which is exactly right.

### Why structured outputs everywhere?

Every agent returns a Pydantic model, not free-form text. This means:

- The orchestrator can reliably parse what the researcher found
- The critic can score the plan against exact fields
- The frontend can render the itinerary without fragile string parsing
- Tests can assert on specific fields

Structured outputs are one of the most important production patterns in agentic AI.

### Why a critic agent instead of just a longer prompt?

A critic agent creates a **revision loop** — the plan goes back for a second pass if
the score is too low. This is impossible with a single prompt. It also lets you tune
the critic independently: you can make the critic stricter or more lenient without
touching the planner. Separation of concerns.

### Why stream the response?

Trip planning takes 15-30 seconds. If you wait for the full response before showing
anything, the user sees a blank screen. Streaming lets you show intermediate steps:
"Researching Tokyo... Finding flights... Building itinerary...". This is a much better
user experience and surprisingly easy to implement with FastAPI's `StreamingResponse`.

---

## Request lifecycle (step by step)

1. User fills in the trip form in the Next.js UI
2. UI sends `POST /api/trip` to the FastAPI backend
3. Backend validates the request, creates a `trip_id`, starts a LangGraph execution
4. LangGraph enters the Orchestrator node
5. Orchestrator queries ChromaDB for user preferences
6. Orchestrator creates a `TaskPlan` — a structured JSON describing what each agent should do
7. LangGraph runs the Researcher node — it uses Tavily to search for destination info
8. LangGraph runs the Planner node — it builds a day-by-day itinerary using Maps API
9. LangGraph runs the Booker node — it fetches real flight and hotel prices from Amadeus
10. LangGraph runs the Critic node — it scores the plan (budget fit, pace, preferences)
11. If score < 7/10, graph loops back to the Orchestrator with the critique
12. Orchestrator adjusts the task plan and re-runs the relevant agents (max 3 revisions)
13. Final plan is serialised to JSON, saved to the database
14. FastAPI returns the plan to the frontend
15. Frontend renders the itinerary with a map, timeline, and price breakdown

---

## Error handling strategy

Each agent can fail independently. The graph handles this by:

- Each tool call is wrapped in a try/except that returns a structured error
- The orchestrator checks each agent's output for error states
- If the booker fails (API down), the orchestrator marks prices as "estimate"
  and continues — a degraded result is better than no result
- Maximum 3 revision loops to prevent infinite cycling

---

## Folder structure alignment

```
This doc ↔ docs/01-architecture.md
Backend code → backend/
Agent code → agents/
Memory code → memory/
Tool wrappers → tools/
```

Next: read `docs/02-agents.md` to understand each agent's responsibilities in detail.