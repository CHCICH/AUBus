# maps_helpers.py
import os
import requests

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    API_KEY = None

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

def geocode_address(address):
    if not API_KEY:
        return None
    params = {"address": address, "key": API_KEY}
    r = requests.get(GEOCODE_URL, params=params, timeout=10)
    data = r.json()
    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None

def reverse_geocode(lat, lng):
    if not API_KEY:
        return None
    params = {"latlng": f"{lat},{lng}", "key": API_KEY}
    r = requests.get(GEOCODE_URL, params=params, timeout=10)
    return r.json()

def get_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode="driving"):
    if not API_KEY:
        return None
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "mode": mode,
        "key": API_KEY
    }
    r = requests.get(DIRECTIONS_URL, params=params, timeout=10)
    return r.json()

def distance_matrix(origins, destinations, mode="driving"):
    if not API_KEY:
        return None
    origins_str = "|".join(f"{lat},{lng}" for lat,lng in origins)
    dests_str = "|".join(f"{lat},{lng}" for lat,lng in destinations)
    params = {"origins": origins_str, "destinations": dests_str, "mode": mode, "key": API_KEY}
    r = requests.get(DISTANCE_MATRIX_URL, params=params, timeout=10)
    return r.json()
