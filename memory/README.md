# Memory System

Three tiers of memory. Each has a different purpose, lifespan, and storage backend.
Full design rationale in `docs/03-memory.md`. This file covers the code structure.

---

## Folder structure

```
memory/
├── README.md           ← you are here
├── session.py          ← TripState definition (Tier 1)
├── preferences.py      ← ChromaDB preference store (Tier 2)
├── history.py          ← SQLite/Postgres trip history (Tier 3)
└── chroma_db/          ← ChromaDB local storage (gitignored)
```

---

## Tier 1 — Session (TripState)

Defined in `memory/session.py`. This is the LangGraph state TypedDict.
See `docs/01-architecture.md` for the full schema.

---

## Tier 2 — Preferences (ChromaDB)

### Reading preferences

```python
# memory/preferences.py

def get_preferences(user_id: str, context: str, n_results: int = 10) -> list[PreferenceSignal]:
    """
    Retrieves the most relevant preference signals for the given user and context.
    'context' is a string describing the current trip (e.g. "Japan street food solo travel")
    """
    collection = get_collection()
    results = collection.query(
        query_texts=[context],
        where={"user_id": user_id},
        n_results=n_results
    )
    return [PreferenceSignal(**json.loads(doc)) for doc in results["documents"][0]]
```

### Writing preferences

```python
def update_preferences(user_id: str, signals: list[PreferenceSignal]) -> None:
    """
    Called by the backend after a trip plan is approved.
    Upserts preference signals into ChromaDB.
    """
    collection = get_collection()
    for signal in signals:
        doc_id = f"{user_id}_{signal.category}_{signal.signal[:20]}"
        collection.upsert(
            ids=[doc_id],
            documents=[json.dumps(signal.model_dump())],
            metadatas=[{"user_id": user_id, "category": signal.category}]
        )
```

---

## Tier 3 — Trip History (SQLite)

```python
# memory/history.py

def get_recent_trips(user_id: str, limit: int = 5) -> list[TripSummary]:
    with get_session() as session:
        trips = session.query(Trip)\
            .filter(Trip.user_id == user_id)\
            .order_by(Trip.created_at.desc())\
            .limit(limit)\
            .all()
        return [TripSummary.from_orm(t) for t in trips]

def save_trip(trip_id: str, user_id: str, plan: TripPlan) -> None:
    with get_session() as session:
        trip = Trip(
            id=trip_id,
            user_id=user_id,
            destination=plan.destination,
            start_date=plan.dates.start,
            end_date=plan.dates.end,
            budget_eur=plan.budget_eur,
        )
        trip_plan = TripPlanRecord(
            trip_id=trip_id,
            plan_json=plan.model_dump_json(),
            critic_score=plan.critic_score,
            revision_count=plan.revision_count
        )
        session.add(trip)
        session.add(trip_plan)
        session.commit()
```

---

## Deleting all data for a user

```python
def delete_user_data(user_id: str) -> None:
    # Delete from ChromaDB
    collection = get_collection()
    collection.delete(where={"user_id": user_id})

    # Delete from SQLite
    with get_session() as session:
        session.query(TripPlanRecord)\
            .filter(TripPlanRecord.trip_id.in_(
                session.query(Trip.id).filter(Trip.user_id == user_id)
            ))\
            .delete(synchronize_session=False)
        session.query(Trip).filter(Trip.user_id == user_id).delete()
        session.query(User).filter(User.id == user_id).delete()
        session.commit()
```