import json
import sqlite3
import time
import requests

def get_weather_api_key():
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('API_WEATHER_KEY='):
                    return line.strip().split('=')[1]
    except FileNotFoundError:
        return None
    return None

WEATHER_API_KEY = get_weather_api_key()

def get_weather_info(data):
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if not WEATHER_API_KEY:
        return {"status": "500", "message": "Weather API key not found"}
    if latitude is None or longitude is None:
        return {"status": "400", "message": "Missing latitude or longitude"}
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": str(response.status_code), "message": "Failed to retrieve weather data"}
    except requests.RequestException as e:
        return {"status": "500", "message": f"Error connecting to weather service: {str(e)}"}



