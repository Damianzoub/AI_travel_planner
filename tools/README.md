# Tools

Wrappers around every external API. Agents never call APIs directly — they call
these wrappers.

---

## Folder structure

```
tools/
├── README.md               ← you are here
├── base.py                 ← BaseTool with retry logic, logging, error handling
├── search.py               ← TavilySearchTool
├── weather.py              ← WeatherTool (OpenWeatherMap)
├── flights.py              ← AmadeusFlightsTool
├── hotels.py               ← AmadeusHotelsTool
├── maps.py                 ← GoogleMapsDirectionsTool + GoogleMapsPlacesTool
├── vision.py               ← VisionValidationTool (Claude API)
└── mocks/
    ├── mock_search.py      ← returns fixture data for tests
    ├── mock_flights.py
    └── mock_maps.py
```

---

## BaseTool

Every tool extends `BaseTool`. It handles:

- Automatic retries (3 attempts, exponential backoff: 1s, 2s, 4s)
- Structured error returns (never raises unhandled exceptions)
- Latency logging

```python
class BaseTool:
    name: str
    max_retries: int = 3

    def call(self, **kwargs) -> ToolResult:
        for attempt in range(self.max_retries):
            try:
                start = time.time()
                data = self._call(**kwargs)
                latency = int((time.time() - start) * 1000)
                return ToolResult(success=True, data=data, latency_ms=latency)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return ToolResult(success=False, error=str(e), latency_ms=0)
                time.sleep(2 ** attempt)

    def _call(self, **kwargs) -> dict:
        raise NotImplementedError
```

---

## Using mocks in tests

Every tool accepts a `mock` flag. In tests, instantiate with `use_mock=True`
and the tool returns data from `tools/mocks/` instead of calling the real API:

```python
# In tests:
flight_tool = AmadeusFlightsTool(use_mock=True)

# In production:
flight_tool = AmadeusFlightsTool()
```

Full API documentation for each tool is in `docs/04-tools.md`.