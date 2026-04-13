import os
from typing import Dict,List,Any

from tavily import TavilyClient

def research_destination(destination:str,interests:List[str])->Dict[str,Any]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set.")
    
    client = TavilyClient(api_key=api_key)
    # This query is intentionally narrow and travel-oriented.
    query = (
        f"Best things to do in {destination} for a traveler interested in "
        f"{', '.join(interests)}. Include neighborhoods, attractions, local food, and practical highlights."
    )

    response = client.search(
        query=query,
        topic='general',
        max_results=1,
        include_answer='advanced',
        include_raw_content=False
    )

    results = response.get('results',[])
    answer = response.get('answer',"")

    candidates = []
    for item in results[:3]:
        title = item.get("title","")
        url = item.get("url","")
        content = item.get("content","")
        candidates.append({
            'title':title,
            'url':url,
            'snippet':content
        })
    
    return {
        "destination":destination,
        "interests":interests,
        "summary":answer,
        "sources":candidates
    }