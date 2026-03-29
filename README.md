# TravelMind 

> A multi-agent AI travel planner — built to demonstrate real agentic AI patterns:
> orchestration, tool use, multi-modal reasoning, and persistent memory.

---

## What this project is

TravelMind is a full-stack agentic AI application. You describe a trip ("5 days in
Tokyo, budget €1500, I love street food and avoid touristy spots") and a network of
specialised AI agents collaborates to produce a complete, validated, bookable itinerary.

This is not a chatbot wrapper. It uses:

- **Multi-agent orchestration** — a supervisor agent that delegates to specialists
- **Real tool use** — live flight prices, hotel availability, maps routing
- **A critic-revisor loop** — the plan is scored and revised before delivery
- **Persistent memory** — the system learns your preferences across trips
- **Multi-modal reasoning** — photos of places are analysed to validate quality

This project is designed as a portfolio piece. Every architectural decision is
documented so you can explain it confidently in interviews.

---

## Repository map

```
travelmind/
│
├── README.md                   ← you are here
│
├── docs/
│   ├── 01-architecture.md      ← system design, data flow, design decisions
│   ├── 02-agents.md            ← what each agent does and why it exists
│   ├── 03-memory.md            ← memory tiers: session, vector, history
│   ├── 04-tools.md             ← every external API and how it is used
│   └── 05-agentic-patterns.md  ← the patterns this project demonstrates (CV gold)
│
│
├── agents/
│   ├── README.md               ← how agents are structured and communicate
│   ├── orchestrator/
│   │   └── README.md           ← the supervisor: plans, delegates, resolves conflicts
│   ├── researcher/
│   │   └── README.md           ← finds destinations, facts, weather, visa info
│   ├── planner/
│   │   └── README.md           ← builds the day-by-day itinerary
│   ├── booker/
│   │   └── README.md           ← queries real flight and hotel APIs
│   └── critic/
│       └── README.md           ← scores the plan, triggers revision loop
│
├── memory/
│   └── README.md               ← 3-tier memory: session, vector store, trip history
│
├── tools/
│   └── README.md               ← API wrappers, search, vision tools
│
├── evals/
|    └── README.md               ← how to measure if the system actually works
|
├── app.py
```

---

## The flow in one picture

```
User: "Plan 5 days in Tokyo, budget €1500, I love street food"
          │
          ▼
    Orchestrator  ←────────  Memory (your prefs + past trips)
          │
          ├──► Researcher   web search · weather · visa rules
          │
          ├──► Planner      day-by-day route · maps · place photos
          │
          ├──► Booker       real flight prices · hotel availability
          │
          └──► Critic       score vs constraints → revise if needed
                    │
                    ▼
          Final itinerary delivered to user
```

## How to read this repo

Read in this order:

1. `docs/01-architecture.md` — understand the full system before touching any code
2. `docs/02-agents.md` — understand what each agent is responsible for
3. `agents/README.md` — understand how agents are coded and wired together
4. `backend/README.md` — understand the server layer
5. `frontend/README.md` — understand the UI layer
6. `docs/05-agentic-patterns.md` — understand what this demonstrates on a CV

---

## Why agents instead of one big prompt?

A single LLM call cannot reliably do all of this:

- Search the web for current prices
- Validate visa requirements for a specific passport
- Optimise a multi-day route across a city
- Check if a restaurant is still open
- Analyse a photo to verify a hotel looks like its listing
- Score the whole plan against a budget constraint
- Revise specific parts without breaking others

Each task needs its own reasoning loop, its own tools, and its own output format.
Agents let you decompose the problem into units that can each be tested, improved,
and monitored independently. That is the core engineering argument for multi-agent
systems, and the argument you will make in every interview about this project.