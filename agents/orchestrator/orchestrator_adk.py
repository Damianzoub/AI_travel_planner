from google.adk import Agent
from pydantic import BaseModel,Field
from typing import List 

#input schema
class TripRequest(BaseModel):
    destination:str
    start_date:str
    end_date:str
    budget:int
    interests:List[str]
    pace:str 

#output schema
class TripPlan(BaseModel):
    destination:str
    trip_summary:str
    days:List[str]


#agent
orchestrator = Agent(
    name="travel_orchestrator",
    model="gemini-2.5-flash-lite",
    description="Creates a structured travel plan from user request",
    instruction="""
    You are a travel planning assistant.
    Take a trip request and produce:
    - A short summary of the trip
    - A simple day-by-day outline
    Keep it realistic, not generic.
    Respect the budget and pace.
""",
output_schema=TripPlan
)