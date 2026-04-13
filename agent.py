import os 
from dotenv import load_dotenv
from google.adk.apps import App

from agents.orchestrator.orchestrator_adk import orchestrator

load_dotenv()

APP_NAME = os.getenv("APP_NAME","travelmind")

app = App(
    name=APP_NAME,
    root_agent=orchestrator
)