import math
import os
import sys
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from safety_score import compute_safety_score
from route_engine import haversine


def build_navigation_payload(route: Dict[str, Any], hour: int = 22, route_type: str = "safest") -> Dict[str, Any]:
    coords = route.get("coordinates", [])
    distance_km = float(route.get("distance_km", 0.0) or 0.0)
    risk_score = float(route.get("total_risk_score", 0.5) or 0.5)
    safety_score = max(0.0, 1.0 - risk_score)

    # Lightweight heuristics for the live navigation card.
    traffic_score = 0.72
    weather_score = 0.80
    crowd_score = 0.70
    hazard_score = 0.75
    final_ai_score = round((safety_score * 0.45) + (traffic_score * 0.2) + (weather_score * 0.15) + (crowd_score * 0.1) + (hazard_score * 0.1), 3)
    eta_minutes = max(3, int(distance_km * 8.0))

    if coords:
        sample = coords[0]
        safety = compute_safety_score(sample[0], sample[1], hour)
        safety_score = safety["score"]

    instructions = generate_turn_instructions(coords, 0)
    return {
        "route_type": route_type,
        "distance_km": round(distance_km, 2),
        "eta_minutes": eta_minutes,
        "safety_score": round(1.0 - risk_score, 3),
        "traffic_score": round(traffic_score, 3),
        "weather_score": round(weather_score, 3),
        "crowd_score": round(crowd_score, 3),
        "hazard_score": round(hazard_score, 3),
        "final_ai_score": round(final_ai_score, 3),
        "risk_level": route.get("risk_level", "MEDIUM"),
        "instructions": instructions,
        "route_points": coords,
        "current_road": "Main Road",
        "next_road": "Bridge Avenue",
    }


def generate_turn_instructions(coords: List[tuple], idx: int = 0) -> Dict[str, Any]:
    if not coords or len(coords) < 2:
        return {"text": "Destination Ahead", "kind": "destination"}

    start = coords[idx]
    nxt = coords[idx + 1] if idx + 1 < len(coords) else coords[-1]
    lat_delta = nxt[0] - start[0]
    lon_delta = nxt[1] - start[1]

    if abs(lat_delta) < 0.0003 and abs(lon_delta) < 0.0003:
        text = "Continue Straight"
        kind = "straight"
    elif lon_delta > 0:
        text = "Turn Right"
        kind = "right"
    else:
        text = "Turn Left"
        kind = "left"

    if idx >= len(coords) - 2:
        text = "Destination Ahead"
        kind = "destination"

    return {"text": text, "kind": kind}


def build_live_navigation_state(route: Dict[str, Any], hour: int = 22) -> Dict[str, Any]:
    payload = build_navigation_payload(route, hour=hour)
    payload["live_status"] = {
        "speed_kmph": 24,
        "gps_accuracy_m": 10,
        "battery_saver": True,
        "voice_guidance": False,
        "alerts": [],
    }
    return payload
