from google.adk import Agent
from pydantic import BaseModel,Field
from typing import List 
from tools.research import research_destination
#input schema
class TripRequest(BaseModel):
    destination:str
    start_date:str
    end_date:str
    budget:int
    interests:List[str]
    pace:str 

class DayPlan(BaseModel):
    day:int = Field(description='Day number starting from 1')
    title:str = Field(description='short title for the day')
    activities:List[str] = Field(description="Main activities for the day")

#output schema
class TripPlan(BaseModel):
    destination:str
    trip_summary:str
    highlights:List[str]


#agent
orchestrator = Agent(
    name="travel_orchestrator",
    model="gemini-2.5-flash-lite",
    description="Creates a structured travel plan from user request",
    instruction="""
You are a travel planner.

First call research_destination.

After that, return the final answer only as a structured TripPlan object.

Rules:
- Do not write markdown.
- Do not write prose outside the schema.
- Do not invent tool names.
- Use only the registered tools.
- The final response must match the TripPlan schema exactly.
""",
output_schema=TripPlan,
    tools=[research_destination]
)