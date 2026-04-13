from __future__ import annotations 
from typing import Any,Dict,List
import requests 
import os 
from datetime import date  
from dotenv import load_dotenv
from tools.code_to_text import mapping
load_dotenv()
GEOCODE_URL = os.getenv('GEOCODE_URL')
FORECAST_URL = os.getenv('FORECAST_URL')
MAX_FORECAST_DAYS=16
def check_exist() -> None:
    if GEOCODE_URL is None:
        raise ValueError("URL error")
    if FORECAST_URL is None:
        raise ValueError("URL error")
    

def _weather_code_to_text(code:int)->str:
    return mapping.get(code,'mixed conditions')

def get_weather_forecast(
    destination: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:

    today = date.today()
    start = date.fromisoformat(start_date)

    days_ahead = (start - today).days

    if days_ahead > MAX_FORECAST_DAYS:
        return {
            "destination": destination,
            "resolved_location": destination,
            "days": [],
            "planning_notes": ["Weather status to be announced"],
        }

    if days_ahead < 0:
        return {
            "destination": destination,
            "resolved_location": destination,
            "days": [],
            "planning_notes": ["Trip date is in the past"],
        }


    geo_resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": destination, "count": 1},
        timeout=20,
    )
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()

    if not geo_data.get("results"):
        raise ValueError(f"Could not resolve destination: {destination}")

    place = geo_data["results"][0]
    lat = place["latitude"]
    lon = place["longitude"]

    forecast_resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date,
        },
        timeout=20,
    )
    forecast_resp.raise_for_status()
    forecast = forecast_resp.json()

    daily = forecast.get("daily", {})

    rdaily = forecast.get("daily", {})

    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_probability_max", [])
    codes = daily.get("weather_code", [])

    days = []

    for i in range(len(dates)):
        days.append({
            "date": dates[i],
            "temp_min_c": tmin[i],
            "temp_max_c": tmax[i],
            "precipitation_probability": precip[i],
            "weather_code": codes[i],
        })

    return {
        "destination": destination,
        "resolved_location": place["name"],
        "days": days,
        "planning_notes": [],  # keep empty or minimal
    }