import os 
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv

client = TavilyClient(api_key=os.getenv('TAVILY_TEST_API'))

response = client.search(
    query='Best food and culture activities in Barcelona for a first time traveler',
    topic='general',
    max_results=3,
    include_answer='advanced'
)
print(response)