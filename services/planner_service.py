import asyncio 
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agent import app
import json
load_dotenv()

_runner = InMemoryRunner(app=app)

def _build_prompt(request:dict) -> str:
    return (
        f"Plan a trip to {request['destination']} from {request['start_date']} "
        f"to {request['end_date']}. Budget: {request['budget']} euros. "
        f"Interests: {', '.join(request['interests'])}. "
        f"Pace: {request['pace']}."
    )

async def _run_agent_async(request:dict):
    prompt = _build_prompt(request)
    return await _runner.run_debug(prompt)


def extract_final_json(events) -> dict:
    for event in reversed(events):
        # Event object -> content attribute
        content = getattr(event, "content", None)
        if content is None:
            continue

        parts = getattr(content, "parts", None)
        if not parts:
            continue

        for part in parts:
            text = getattr(part, "text", None)
            if not text:
                continue

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue

    raise ValueError("No final JSON response found in ADK events.")

def generate_trip_plan(request:dict):
    events = asyncio.run(_run_agent_async(request))
    final_result = extract_final_json(events)
    return final_result