import math
import os
import sys
from typing import List, Dict, Any

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from safety_score import compute_safety_score
from route_engine import haversine


def normalize_osm_parking_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize raw OpenStreetMap/Overpass parking records into SafeRoute's parking schema."""
    elements = payload.get("elements", []) if isinstance(payload, dict) else []
    normalized = []
    for element in elements:
        if element.get("type") not in {"node", "way", "relation"}:
            continue
        tags = element.get("tags", {}) or {}
        if not tags:
            continue
        if tags.get("amenity") not in {"parking", "parking_space", "bicycle_parking"} and "parking" not in tags.get("amenity", ""):
            continue
        name = tags.get("name") or tags.get("operator") or "Nearby Parking"
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            continue
        parking_type = "Covered" if tags.get("covered") == "yes" else "Open"
        capacity = int(tags.get("capacity", 0) or 0)
        fee = tags.get("fee") == "yes"
        wheelchair = tags.get("wheelchair") == "yes" or tags.get("access") == "wheelchair"
        normalized.append({
            "id": f"osm-{len(normalized)+1}",
            "name": name,
            "latitude": round(float(lat), 6),
            "longitude": round(float(lon), 6),
            "parking_type": parking_type,
            "capacity": capacity or 50,
            "available_spaces": max(1, int(capacity or 50) // 2),
            "occupied_spaces": max(1, int(capacity or 50) // 2),
            "availability_percentage": 55,
            "parking_fee": 0 if not fee else 20,
            "opening_hours": tags.get("opening_hours", "24/7"),
            "max_vehicle_height_m": 2.1,
            "ev_charging": tags.get("ev_charging") == "yes",
            "covered": parking_type == "Covered",
            "wheelchair_accessible": wheelchair,
            "walking_distance_m": 120,
            "estimated_walking_time_min": 2,
            "parking_safety_score": 90,
            "crime_score": 18,
            "lighting_score": 80,
            "cctv_score": 75,
            "crowd_density_score": 50,
            "traffic_score": 80,
            "road_hazard_score": 82,
            "weather_risk": 12,
            "police_proximity": 80,
            "hospital_proximity": 78,
            "night_safety_score": 90,
            "final_score": 0,
            "source": "osm",
        })
    return normalized


def fetch_osm_parking(destination_lat: float, destination_lon: float, radius_m: int = 800) -> List[Dict[str, Any]]:
    """Attempt to fetch parking data from OpenStreetMap/Overpass. Returns empty list if unavailable."""
    if requests is None:
        return []

    overpass_query = f"""
    [out:json][timeout:10];
    node[amenity~'parking|parking_space|bicycle_parking'](around:{radius_m},{destination_lat},{destination_lon});
    out center 20;
    """
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        return normalize_osm_parking_records(payload)
    except Exception:
        return []


def build_parking_candidates(destination_lat: float, destination_lon: float, radius_m: int = 800, hour: int = 22) -> List[Dict[str, Any]]:
    """Create parking candidates around a destination using live OSM data when available, otherwise deterministic heuristics."""
    candidates = []
    live_candidates = fetch_osm_parking(destination_lat, destination_lon, radius_m=radius_m)
    if live_candidates:
        candidates.extend(live_candidates)
        return candidates

    offset_steps = [
        (-0.0006, -0.0006), (0.0006, -0.0006), (-0.0006, 0.0006), (0.0006, 0.0006),
        (0.0000, -0.0008), (0.0000, 0.0008), (-0.0008, 0.0000), (0.0008, 0.0000),
    ]

    for idx, (lat_off, lon_off) in enumerate(offset_steps):
        lat = destination_lat + lat_off
        lon = destination_lon + lon_off
        walking_distance_m = max(80, int(haversine((destination_lat, destination_lon), (lat, lon)) * 1000))
        safety = compute_safety_score(lat, lon, hour)
        availability_pct = 70 + ((idx % 4) * 7)
        parking_type = "Open" if idx % 2 == 0 else "Covered"
        capacity = 40 + idx * 15
        occupied = int(capacity * (1 - availability_pct / 100))
        available = capacity - occupied

        candidate = {
            "id": f"parking-{idx+1}",
            "name": f"AI Parking {idx+1}",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "parking_type": parking_type,
            "capacity": capacity,
            "available_spaces": available,
            "occupied_spaces": occupied,
            "availability_percentage": availability_pct,
            "parking_fee": 20 + (idx % 3) * 10,
            "opening_hours": "24/7",
            "max_vehicle_height_m": 2.1 + (idx % 2) * 0.2,
            "ev_charging": idx % 2 == 0,
            "covered": parking_type == "Covered",
            "wheelchair_accessible": True,
            "walking_distance_m": walking_distance_m,
            "estimated_walking_time_min": max(2, round(walking_distance_m / 80)),
            "parking_safety_score": round(100 * (1 - safety["score"]), 1),
            "crime_score": round(100 * safety["crime_density"], 1),
            "lighting_score": round(100 * safety["lighting"], 1),
            "cctv_score": round(100 * safety["cctv"], 1),
            "crowd_density_score": round(100 * safety["crowd"], 1),
            "traffic_score": 80 - (idx * 3),
            "road_hazard_score": 85 - (idx * 4),
            "weather_risk": 10 + (idx % 3) * 8,
            "police_proximity": 75 + (idx % 3) * 6,
            "hospital_proximity": 70 + (idx % 3) * 7,
            "night_safety_score": round(100 * (1 - safety["score"]), 1),
            "final_score": 0,
        }
        candidates.append(candidate)

    return candidates


def recommend_parking(candidates: List[Dict[str, Any]], destination_lat: float, destination_lon: float, hour: int = 22) -> List[Dict[str, Any]]:
    """Score and rank parking candidates for the safest and most suitable option."""
    ranked = []
    for candidate in candidates:
        final_score = (
            candidate["parking_safety_score"] * 0.30 +
            candidate["availability_percentage"] * 0.20 +
            candidate["traffic_score"] * 0.15 +
            candidate["lighting_score"] * 0.10 +
            candidate["cctv_score"] * 0.10 +
            candidate["night_safety_score"] * 0.10 +
            max(0, 100 - candidate["walking_distance_m"] / 5) * 0.05
        )
        candidate["final_score"] = round(final_score, 1)
        candidate["reason"] = build_reason(candidate)
        ranked.append(candidate)

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked


def build_reason(candidate: Dict[str, Any]) -> str:
    if candidate["availability_percentage"] >= 80:
        availability_text = "plenty of space"
    elif candidate["availability_percentage"] >= 60:
        availability_text = "moderate availability"
    else:
        availability_text = "limited availability"

    if candidate["lighting_score"] >= 80:
        lighting_text = "excellent lighting"
    else:
        lighting_text = "moderate lighting"

    return f"Best balance of safety, {availability_text}, and {lighting_text}."


def build_walking_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, hour: int = 22) -> List[List[float]]:
    """Generate a simple walking-route polyline from parking to destination."""
    steps = 4
    lat_step = (end_lat - start_lat) / steps
    lon_step = (end_lon - start_lon) / steps
    points = []
    for i in range(steps + 1):
        lat = start_lat + (lat_step * i)
        lon = start_lon + (lon_step * i)
        points.append([round(lat, 6), round(lon, 6)])
    return points


def build_parking_payload(destination_lat: float, destination_lon: float, radius_m: int = 800, hour: int = 22) -> Dict[str, Any]:
    candidates = build_parking_candidates(destination_lat, destination_lon, radius_m=radius_m, hour=hour)
    ranked = recommend_parking(candidates, destination_lat=destination_lat, destination_lon=destination_lon, hour=hour)
    best = ranked[0] if ranked else None
    walking_route = []
    if best:
        walking_route = build_walking_route(destination_lat, destination_lon, best["latitude"], best["longitude"], hour=hour)
    return {
        "destination": {"lat": destination_lat, "lon": destination_lon},
        "radius_m": radius_m,
        "recommendations": ranked[:4],
        "best_parking": best,
        "walking_route": walking_route,
    }
