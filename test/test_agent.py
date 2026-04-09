import asyncio
import json
import os
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.orchestrator.orchestrator_adk import orchestrator, TripRequest

load_dotenv()

APP_NAME = os.getenv("APP_NAME")
USER_ID = os.getenv("USER_ID")
SESSION_ID = os.getenv("SESSION_ID")


async def main():
    request = TripRequest(
        destination="Barcelona, Spain",
        start_date="2026-06-10",
        end_date="2026-06-14",
        budget=1500,
        interests=["food", "culture"],
        pace="balanced"
    )

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

    runner = Runner(
        agent=orchestrator,
        app_name=APP_NAME,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(request.model_dump()))]
    )

    for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
        if event.is_final_response():
            print(event.content)


asyncio.run(main())
