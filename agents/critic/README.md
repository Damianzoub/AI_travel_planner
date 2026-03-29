# Critic Agent

Quality control. The only agent that can reject a plan and trigger a revision.
The most important agent for demonstrating sophisticated agentic behaviour.

---

## Single responsibility

Score the assembled plan (itinerary + booking options) against five dimensions.
If the score is below the threshold, produce specific, actionable feedback for
the orchestrator. If approved, pass the plan through.

---

## What it reads from state

```python
state["itinerary"]         # from the planner
state["booking_options"]   # from the booker
state["task_plan"]         # the original plan (to check constraints)
state["revision_count"]    # to enforce the 3-loop maximum
```

## What it writes to state

```python
state["critique"]  # Critique object
```

---

## Scoring dimensions

Each dimension is scored 0–10:

| Dimension | Weight | What it checks |
|-----------|--------|----------------|
| Budget fit | 30% | Does total cost ≤ user budget? |
| Pace | 20% | Are there 2–4 activities per day? Not packed, not empty? |
| Preference alignment | 25% | Do the chosen places match stated interests? |
| Practicality | 15% | Are opening hours respected? Is transit realistic? |
| Diversity | 10% | Is there a mix of experiences across days? |

**Total score = weighted sum**. Approval threshold: 7.0 / 10.

---

## Decision logic

```python
total_score = compute_weighted_score(dimension_scores)

if state["revision_count"] >= 3:
    # Force approve — prevent infinite loop
    # Deliver best plan with warnings
    return Critique(approved=True, warnings=["Max revisions reached. Plan delivered as-is."])

if total_score >= 7.0:
    return Critique(approved=True, total_score=total_score)

else:
    issues = identify_specific_issues(dimension_scores)
    fixes = generate_fix_instructions(issues)
    return Critique(
        approved=False,
        total_score=total_score,
        issues=issues,
        suggested_fixes=fixes
    )
```

---

## How issues become fix instructions

The critic does not just say "budget exceeded". It says what to fix:

```python
# Budget over by €340
# → critic output:
issues = ["Total estimated cost is €1840, exceeding the €1500 budget by €340"]
suggested_fixes = [
    "Switch hotel recommendation from 4-star to 3-star (saves ~€200)",
    "Remove one paid attraction from Day 2 (saves ~€50)",
    "Shift dinner on Day 4 from sit-down restaurant to street food market (saves ~€40)"
]
```

The orchestrator receives these and uses them to revise the PlannerTask and
BookerTask before the next loop.

---

## Why this agent matters

Most AI applications:
1. Take user input
2. Call an LLM
3. Return the result

TravelMind:
1. Takes user input
2. Runs four specialist agents
3. Evaluates the result against explicit criteria
4. If it fails, produces structured feedback and retries
5. Delivers the best result seen

This loop is the pattern that makes a system *agentic* rather than just *automated*.
In any interview, this is what you should emphasise: "The system knows when its
output isn't good enough and can fix it without human intervention."

---

## Output schema

```python
class Critique(BaseModel):
    approved: bool
    total_score: float
    dimension_scores: dict[str, float]   # {"budget_fit": 4.0, "pace": 8.0, ...}
    issues: list[str]                    # specific problems
    suggested_fixes: list[str]           # concrete instructions for the orchestrator
    warnings: list[str]                  # soft concerns even if approved

    # Meta
    revision_count: int
    force_approved: bool = False         # True if approved only because max revisions hit
```

---

## Tuning the critic

The approval threshold (7.0) and dimension weights are configurable in `config.py`.
A stricter critic (threshold 8.0) produces better plans but may loop more times.
A more lenient critic (threshold 6.0) is faster but may deliver suboptimal plans.

This tunability is worth mentioning in interviews: "The quality bar is configurable.
You could deploy a 'fast mode' with a lower threshold for users who want quick results,
and a 'quality mode' with a higher threshold for users who don't mind waiting."