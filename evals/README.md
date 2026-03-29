# Evals — Measuring If the System Works

Evaluations are how you know the system is actually good, not just apparently good.
This is an underrated part of AI engineering and worth having on your CV.

---

## Why evals matter

LLM systems can fail silently. The plan looks reasonable but exceeds the budget.
The itinerary has a restaurant that closed two years ago. The vision validator
approves places it shouldn't. Without evals, you only find these failures when
a user complains.

---

## What we evaluate

### 1. End-to-end plan quality

Run the full graph on a set of fixed test cases and score the output:

```
test_cases/
├── tokyo_budget_backpacker.json   # €800, 5 days, street food, hostels
├── paris_romantic_midrange.json   # €2000, 4 days, fine dining, museums
├── barcelona_family.json          # €3000, 7 days, beaches, family-friendly
└── solo_adventure_unknown.json    # vague request, tests intent parsing
```

For each case, run the graph and check:
- Did the plan stay within budget?
- Are all itinerary slots plausible (not null, not impossible)?
- Did the critic approve on the first pass, or how many loops were needed?
- Were all place names real (not hallucinated)?

### 2. Individual agent evals

Each agent has its own eval in `agents/{name}/tests/evals.py`:

```python
# agents/planner/tests/evals.py

def eval_planner_pace():
    """Planner should never schedule more than max_activities_per_day"""
    for test_case in PLANNER_TEST_CASES:
        result = planner.run(test_case["state"])
        itinerary = Itinerary(**result["itinerary"])
        for day in itinerary.days:
            activities = [s for s in day.slots if s.place_type != "transport"]
            assert len(activities) <= test_case["max_activities"], (
                f"Day {day.day_number} has {len(activities)} activities, "
                f"expected max {test_case['max_activities']}"
            )
```

### 3. Critic calibration

The critic should approve ~80% of plans on the first pass. If it approves
everything, the threshold is too low. If it almost never approves, it is too strict.

```python
def eval_critic_approval_rate():
    results = [run_full_graph(case) for case in ALL_TEST_CASES]
    first_pass_approvals = sum(1 for r in results if r["revision_count"] == 0)
    rate = first_pass_approvals / len(results)
    assert 0.6 <= rate <= 0.9, f"Critic approval rate {rate:.0%} out of expected range"
```

---

## Running evals

```bash
# Run all evals
python -m evals.run

# Run one agent's evals only
python -m evals.run --agent planner

# Run with a specific test case
python -m evals.run --case tokyo_budget_backpacker
```

---

## The eval mindset (for interviews)

Being able to talk about evals shows you think about AI systems like an engineer,
not just a demo builder. Two things to say:

"I have a fixed test suite that I run after any prompt change. If the approval rate
or budget adherence drops, I know the change made things worse."

"The hardest part of evals for LLM systems is that the 'correct' answer isn't always
obvious. I use a combination of hard constraints (budget must be within X%) and
LLM-as-judge (asking Claude to score plan quality on the test cases) because the
judge generalises better to edge cases than hand-written rules."

The second point — LLM-as-judge — is a real pattern used in production systems at
Anthropic, OpenAI, and major AI teams. Mentioning it shows you're aware of current practice.