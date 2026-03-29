# 03 — Memory System

TravelMind has three distinct memory tiers. Understanding why three tiers exist,
and what each is for, is important both for building the system and for explaining
it in interviews.

---

## The three tiers

```
┌─────────────────────────────────────────────────────────┐
│  Tier 1: Session Memory                                  │
│  What: The LangGraph state dict for the current trip     │
│  Where: In-process Python dict (RAM)                     │
│  Lifespan: One trip planning session (~30 seconds)       │
│  Used by: All agents (read + write via LangGraph state)  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Tier 2: Preference Memory                               │
│  What: User's travel preferences as vector embeddings   │
│  Where: ChromaDB (local file, or hosted)                 │
│  Lifespan: Persistent across all sessions               │
│  Used by: Orchestrator (reads at start), Critic (writes  │
│           after approval to update the profile)          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Tier 3: Trip History                                    │
│  What: Structured records of completed trips             │
│  Where: SQLite (dev) / Postgres (production)             │
│  Lifespan: Permanent                                     │
│  Used by: Orchestrator (reads to infer preferences),    │
│           Frontend (displays history to user)            │
└─────────────────────────────────────────────────────────┘
```

---

## Tier 1 — Session Memory

This is just the LangGraph state. Every agent reads from it and writes back to it.
There is nothing to build here beyond defining the `TripState` TypedDict correctly.

The important thing about session memory is that it is **ephemeral**. When the graph
finishes, the state is gone unless you explicitly save it. The backend is responsible
for persisting anything important to Tier 3 before the session ends.

---

## Tier 2 — Preference Memory (ChromaDB)

### What gets stored

After each completed trip, the critic writes a preference update. This is not a raw
dump of the trip — it is a distilled set of preference signals:

```python
class PreferenceUpdate(BaseModel):
    user_id: str
    signals: list[PreferenceSignal]

class PreferenceSignal(BaseModel):
    category: str         # "accommodation" | "food" | "pace" | "transport" | "style"
    signal: str           # human-readable preference statement
    strength: float       # 0.0 to 1.0 (how strong/reliable this signal is)
    source: str           # "explicit" (user said it) | "inferred" (from trip data)
```

Example signals:
- `{ category: "food", signal: "strongly prefers street food over restaurants", strength: 0.9, source: "explicit" }`
- `{ category: "pace", signal: "prefers 3-4 activities per day, not more", strength: 0.7, source: "inferred" }`
- `{ category: "accommodation", signal: "books 3-star hotels near city centre", strength: 0.85, source: "inferred" }`

### How it is queried

At the start of each session, the orchestrator sends a query like:
`"travel preferences for user {user_id} going to {destination}"`

ChromaDB returns the most semantically similar preference signals. The orchestrator
injects these into its reasoning when creating the TaskPlan:
"This user has previously preferred slow-paced trips. Adjust the planner task to
limit slots to 3 per day."

### Why embeddings instead of a simple key-value store?

Two reasons:

1. **Semantic similarity** — "loves izakayas" and "prefers casual dining" are related
   ideas. A vector store retrieves both when the context is "food preferences Japan".
   A key-value store would only return exact matches.

2. **Scalability** — as the preference store grows over many trips, semantic retrieval
   stays efficient. You don't need to load all preferences and filter manually.

For a portfolio project, this difference may seem academic. But being able to explain
*why* you used a vector store (not just *that* you used one) is exactly what makes
you stand out in an interview.

### ChromaDB setup

```python
import chromadb

client = chromadb.PersistentClient(path="./memory/chroma_db")
collection = client.get_or_create_collection(
    name="user_preferences",
    metadata={"hnsw:space": "cosine"}
)
```

Embeddings are generated using the Anthropic embeddings API or a local model
(all-MiniLM-L6-v2 via sentence-transformers is a good free option).

---

## Tier 3 — Trip History (SQLite / Postgres)

### Schema

```sql
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    passport_country TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trips table
CREATE TABLE trips (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    destination TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    budget_eur FLOAT,
    actual_cost_eur FLOAT,
    status TEXT DEFAULT 'planned',  -- planned | completed | cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full plan stored as JSON (flexible, avoids over-normalisation)
CREATE TABLE trip_plans (
    trip_id TEXT PRIMARY KEY REFERENCES trips(id),
    plan_json TEXT NOT NULL,  -- the full TripPlan as JSON
    critic_score FLOAT,
    revision_count INTEGER DEFAULT 0
);

-- Individual places visited (for preference inference)
CREATE TABLE trip_places (
    id TEXT PRIMARY KEY,
    trip_id TEXT REFERENCES trips(id),
    place_name TEXT,
    place_type TEXT,
    area TEXT,
    user_rating INTEGER,  -- 1-5, filled in post-trip (optional future feature)
    notes TEXT
);
```

### How the orchestrator uses trip history

At the start of a session, the orchestrator runs a query like:

```sql
SELECT t.destination, t.budget_eur, t.actual_cost_eur, tp.critic_score
FROM trips t
JOIN trip_plans tp ON t.id = tp.trip_id
WHERE t.user_id = ?
ORDER BY t.created_at DESC
LIMIT 5
```

It feeds this structured data into its prompt:
"This user has taken 3 previous trips. Average budget: €1200. Average actual spend: €980.
They have visited Japan once before. Adjust recommendations to avoid repetition."

---

## Memory lifecycle

```
New user → no memory → orchestrator uses only explicit user input

After first trip:
  Critic writes preference signals → ChromaDB (Tier 2)
  Backend saves trip record → SQLite (Tier 3)

Second trip:
  Orchestrator reads ChromaDB (Tier 2) → enriches TaskPlan
  Orchestrator reads SQLite (Tier 3) → avoids repetition, calibrates budget

Over time:
  Preference signals accumulate → system becomes increasingly personalised
```

---

## Privacy considerations (important for your CV)

If someone asks "how do you handle user data?", here is the answer this architecture
supports:

- All memory is keyed by `user_id` — deleting a user deletes all their memory
- Preference signals are distilled (not raw trip data) — the system stores inferences,
  not transcripts
- ChromaDB data can be exported or cleared per user
- SQLite/Postgres records can be deleted on request (GDPR-compatible design)

Being able to speak to data privacy shows engineering maturity.

---

Next: read `docs/04-tools.md` to understand every external API used.