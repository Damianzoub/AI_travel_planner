# Agents — How They Are Built

This folder contains all five agents. Read this before reading any individual
agent's README.

---

## Folder structure

```
agents/
├── README.md               ← you are here
├── orchestrator/
│   ├── README.md
│   ├── agent.py            ← the orchestrator class
│   ├── prompts/
│   │   └── v1.txt          ← system prompt (versioned)
│   └── tests/
│       └── test_agent.py
├── researcher/
│   ├── README.md
│   ├── agent.py
│   ├── prompts/v1.txt
│   └── tests/
├── planner/
│   ├── README.md
│   ├── agent.py
│   ├── prompts/v1.txt
│   └── tests/
├── booker/
│   ├── README.md
│   ├── agent.py
│   ├── prompts/v1.txt
│   └── tests/
└── critic/
    ├── README.md
    ├── agent.py
    ├── prompts/v1.txt
    └── tests/
```

---

## How every agent is structured

Every agent follows the same pattern:

```python
class BaseAgent:
    def __init__(self, tools: list[BaseTool], model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic()
        self.tools = tools
        self.model = model
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "v1.txt"
        return prompt_path.read_text()

    def run(self, state: TripState) -> dict:
        """
        Takes the current trip state, does its job, returns
        a dict of state updates (not a full TripState).
        """
        raise NotImplementedError

    def _call_llm(self, messages: list, output_schema: type[BaseModel]) -> BaseModel:
        """
        Calls Claude with forced tool use to guarantee structured output.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            tools=[{
                "name": "structured_output",
                "description": "Return your result in this exact format",
                "input_schema": output_schema.model_json_schema()
            }],
            tool_choice={"type": "tool", "name": "structured_output"},
            messages=messages
        )
        return output_schema(**response.content[0].input)
```

---

## How agents fit into the LangGraph graph

Each agent's `run()` method is wrapped in a LangGraph node:

```python
from langgraph.graph import StateGraph, END
from agents.orchestrator.agent import OrchestratorAgent
from agents.researcher.agent import ResearcherAgent
# ... etc

def build_graph() -> StateGraph:
    graph = StateGraph(TripState)

    # Add nodes
    graph.add_node("orchestrator", OrchestratorAgent().run)
    graph.add_node("researcher", ResearcherAgent().run)
    graph.add_node("planner", PlannerAgent().run)
    graph.add_node("booker", BookerAgent().run)
    graph.add_node("critic", CriticAgent().run)

    # Add edges
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "researcher")
    graph.add_edge("researcher", "planner")
    graph.add_edge("planner", "booker")
    graph.add_edge("booker", "critic")

    # Conditional edge from critic: approve → END, reject → orchestrator
    graph.add_conditional_edges(
        "critic",
        lambda state: "end" if state["critique"]["approved"] else "orchestrator",
        {"end": END, "orchestrator": "orchestrator"}
    )

    return graph.compile()
```

---

## Prompt versioning

Every agent's system prompt lives in `prompts/v1.txt`. When you change a prompt:

1. Create `prompts/v2.txt` with the new prompt
2. Update the agent to load `v2.txt`
3. Keep `v1.txt` so you can roll back if quality drops

Never edit a prompt in place without versioning it. Prompt changes can silently
break downstream agents (e.g. changing the researcher's output format breaks
the planner, which depends on it).

---

## Testing agents

Each agent has a `tests/` folder with unit tests. Tests use mock tools so
they do not make real API calls:

```python
# agents/researcher/tests/test_agent.py

def test_researcher_returns_valid_output():
    mock_search = MockTavilyTool(returns=FAKE_SEARCH_RESULTS)
    agent = ResearcherAgent(tools=[mock_search])

    state = build_test_state(destination="Tokyo")
    updates = agent.run(state)

    assert "destination_research" in updates
    research = DestinationResearch(**updates["destination_research"])
    assert len(research.place_candidates) >= 5
    assert research.weather_summary is not None
```

Run all agent tests: `pytest agents/`

---

Read each agent's individual README for its specific responsibilities, tools,
and output schema. Start with `agents/orchestrator/README.md`.