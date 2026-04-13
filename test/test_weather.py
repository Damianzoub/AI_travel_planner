from tools.weather import get_weather_forecast

results = get_weather_forecast(
    destination='Barcelona, Spain',
    start_date='2026-04-13',
    end_date='2026-04-18'
)
print(results)