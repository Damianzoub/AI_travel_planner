# 05 — Agentic Patterns (Your CV Story)

This document maps what TravelMind demonstrates to the concepts that matter in
2025-2026 AI engineering. Use it to prepare for interviews.

---

## The patterns this project demonstrates

### 1. Supervisor-worker orchestration

**What it is:** A central agent (the orchestrator) that understands the full goal
and delegates subtasks to specialist agents that only need to solve one problem well.

**Where it appears in TravelMind:** The orchestrator creates a TaskPlan and dispatches
it to the researcher, planner, booker, and critic. None of those agents know about
each other.

**Why it matters:** This is the dominant pattern in production multi-agent systems.
It scales because you can add new specialists without changing the core.

**How to explain it:** "The orchestrator acts like a project manager. It knows
the full brief, breaks it into specialised tasks, and each specialist agent works
independently. The orchestrator then assembles the results and handles conflicts."

---

### 2. Tool use (function calling)

**What it is:** An LLM that can call external functions (APIs, search, databases)
as part of its reasoning, not just generate text.

**Where it appears in TravelMind:** Every agent except the orchestrator uses at
least one external tool. The researcher uses Tavily search. The planner uses
Google Maps. The booker calls Amadeus. The planner uses vision.

**Why it matters:** Tool use is what makes agents useful in the real world. Without
it, an LLM can only recite what it learned at training time.

**How to explain it:** "I used Claude's native tool use / function calling to give
each agent access to real-time data. The LLM decides when and how to call each tool
based on the task at hand. I wrapped every API call in a typed tool class that handles
retries, errors, and logging."

---

### 3. The critic-revisor loop (self-evaluation)

**What it is:** A pattern where a separate agent evaluates the primary agent's output
against explicit criteria and sends it back for revision if it falls below a threshold.

**Where it appears in TravelMind:** The critic agent scores the assembled plan across
five dimensions. If the weighted score is below 7/10, it sends specific feedback to
the orchestrator, which adjusts the TaskPlan and re-runs the relevant agents.

**Why it matters:** Most AI projects deliver the first thing the model produces.
The critic-revisor loop makes the system self-correcting. It is the pattern most
often cited as the difference between a prototype and a production system.

**How to explain it:** "The system evaluates its own output against explicit, tunable
criteria — budget fit, pace, preference alignment, practicality, diversity. If a plan
fails, the critic produces structured feedback that the orchestrator uses to revise
specific parts of the plan. This loops up to three times before delivering the best
result seen. The criteria are configurable — you can make the system more or less
strict by adjusting the threshold."

---

### 4. Persistent memory across sessions

**What it is:** An agent system that remembers past interactions and uses them to
improve future responses without being re-told everything each time.

**Where it appears in TravelMind:** ChromaDB stores preference signals extracted
after each trip. The orchestrator retrieves the most relevant signals at the start
of each new session and injects them into the TaskPlan.

**Why it matters:** Memory is what turns a stateless AI tool into a personalised
assistant. It is one of the most-requested features in production AI applications.

**How to explain it:** "I implemented three tiers of memory. Session memory lives
in the LangGraph state — it exists only for the current planning session. Preference
memory lives in ChromaDB as vector embeddings — it is queried semantically so the
system can retrieve relevant past preferences even if they are phrased differently.
Trip history lives in a relational database and is used to infer broader patterns
across trips."

---

### 5. Multi-modal reasoning

**What it is:** An LLM that processes both text and images as part of its reasoning.

**Where it appears in TravelMind:** The planner agent fetches photos of candidate
restaurants and attractions from the Google Places API and sends them to Claude
with a validation prompt. The result influences which places are included in the
itinerary.

**Why it matters:** Multi-modal is increasingly expected in production AI systems.
Being able to work with images — not just text — significantly expands what an
agent can verify and decide.

**How to explain it:** "The planner doesn't just take text descriptions of places
at face value. It fetches the actual photos from Google Places and asks Claude
whether they match the user's stated preferences. A place that claims to be authentic
street food but whose photos show a tourist restaurant interior gets swapped out. This
is a small but concrete example of multi-modal reasoning changing a real decision."

---

### 6. Structured outputs

**What it is:** Using LLM function calling / tool use to guarantee that agent
outputs conform to a defined schema (Pydantic model), rather than parsing free-form text.

**Where it appears in TravelMind:** Every agent output is a Pydantic model. The
LLM is forced to produce outputs that match the schema via Claude's tool use feature.

**Why it matters:** Fragile string parsing is one of the top causes of failure in
production AI systems. Structured outputs make agent handoffs reliable.

**How to explain it:** "Every agent in the system produces a typed Pydantic model,
not free-form text. I use Claude's tool use feature with tool_choice forced, which
means the model is required to produce a valid JSON object matching the schema. This
makes the entire pipeline reliable — the orchestrator can read the researcher's output
as a Python object, not as a string it needs to parse."

---

### 7. State machine orchestration with LangGraph

**What it is:** Using an explicit directed graph to model the flow between agents,
with conditional edges that determine which agent runs next based on the current state.

**Where it appears in TravelMind:** The entire agent flow is a LangGraph graph.
The edge from the critic node is conditional — it either goes to the final output
node or loops back to the orchestrator depending on the critic's approval status.

**Why it matters:** Explicit state machines are debuggable. When something goes wrong,
you can inspect exactly which node was executing and what the state contained.
This is the difference between "the AI did something weird" and "node X received
state Y and produced output Z."

**How to explain it:** "I chose LangGraph because it makes the control flow explicit.
The entire multi-agent system is a directed graph. Every transition between agents is
a named edge. The conditional edge from the critic either exits the graph or loops back,
and that logic is visible in the graph definition. When I need to debug a failed plan,
I can inspect the exact state at every node."

---

## The one-sentence interview summary

"TravelMind is a multi-agent system that uses supervisor-worker orchestration,
real tool use with live APIs, a critic-revisor loop for self-correction, and
persistent vector memory — built on LangGraph, FastAPI, and Claude."

---

## Questions you should be able to answer

- Why did you choose LangGraph over CrewAI?
- How do agents communicate without calling each other directly?
- What happens when the booker API is down?
- How does the system get better over time?
- How would you scale this to 1,000 concurrent users?
- How do you test an agent?
- What does the critic actually score?
- What is the maximum number of revision loops and why?
- How would you add a new specialist agent?
- What data do you store about users and why?

Answers to all of these are in the docs. Re-read them before any interview.