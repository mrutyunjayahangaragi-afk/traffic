"""
Namma Safe BLR — FastAPI Backend
Run:  uvicorn app:app --reload --port 8000
"""

import os, sys, json, pickle
import urllib.request
import urllib.parse
from datetime import datetime
from typing   import Optional

import pandas as pd
import numpy  as np

# ── ensure backend/ is on the path ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from fastapi            import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses  import FileResponse
from pydantic           import BaseModel, Field

import data_processing as dp
import safety_score    as ss
import risk_model      as rm
import route_engine    as re

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Namma Safe BLR API",
    description = "AI-powered safety navigation for Bangalore night travel",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup: load data & model ───────────────────────────────────────────────
BASE    = os.path.dirname(__file__)
DATA_PATH  = os.path.join(BASE, "../data/bangalore_crime_dataset.csv")
MODEL_PATH = os.path.join(BASE, "../models/risk_model.pkl")

crime_df    = None
density_grid = []
model_bundle = None
incidents_log: list = []    # in-memory crowd-reported incidents

KNOWN_LOCATIONS = {
    "mg road": {"latitude": 12.9716, "longitude": 77.5946, "display_name": "MG Road, Bengaluru"},
    "city centre": {"latitude": 12.9716, "longitude": 77.5946, "display_name": "City Centre, Bengaluru"},
    "majestic": {"latitude": 12.9768, "longitude": 77.5713, "display_name": "Majestic, Bengaluru"},
    "ksr": {"latitude": 12.9768, "longitude": 77.5713, "display_name": "KSR Station, Bengaluru"},
    "indiranagar": {"latitude": 12.9716, "longitude": 77.6412, "display_name": "Indiranagar, Bengaluru"},
    "marathahalli": {"latitude": 12.9591, "longitude": 77.6971, "display_name": "Marathahalli, Bengaluru"},
    "hebbal": {"latitude": 13.0358, "longitude": 77.5970, "display_name": "Hebbal, Bengaluru"},
    "yelahanka": {"latitude": 13.1006, "longitude": 77.5964, "display_name": "Yelahanka, Bengaluru"},
    "whitefield": {"latitude": 12.9698, "longitude": 77.7499, "display_name": "Whitefield, Bengaluru"},
    "koramangala": {"latitude": 12.9352, "longitude": 77.6245, "display_name": "Koramangala, Bengaluru"},
    "btm": {"latitude": 12.9165, "longitude": 77.6101, "display_name": "BTM Layout, Bengaluru"},
    "jayanagar": {"latitude": 12.9258, "longitude": 77.5838, "display_name": "Jayanagar, Bengaluru"},
    "electronic city": {"latitude": 12.8452, "longitude": 77.6602, "display_name": "Electronic City, Bengaluru"},
    "bannerghatta": {"latitude": 12.8993, "longitude": 77.5975, "display_name": "Bannerghatta Road, Bengaluru"},
    "shivajinagar": {"latitude": 12.9840, "longitude": 77.5975, "display_name": "Shivajinagar, Bengaluru"},
    "domlur": {"latitude": 12.9609, "longitude": 77.6387, "display_name": "Domlur, Bengaluru"},
}


def _parse_coordinate_query(query: str) -> Optional[dict]:
    if not query:
        return None
    cleaned = query.strip()
    if not cleaned:
        return None
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                return {"latitude": lat, "longitude": lon, "display_name": "User provided coordinates", "source": "coordinates"}
            except ValueError:
                return None
    return None


def geocode_query(query: str) -> dict:
    """Resolve a place name or coordinate string into latitude/longitude values."""
    if not query or not query.strip():
        return {"latitude": 12.9716, "longitude": 77.5946, "display_name": "Bengaluru, Karnataka", "source": "fallback"}

    parsed = _parse_coordinate_query(query)
    if parsed:
        return parsed

    normalized = query.strip().lower()
    for key, value in KNOWN_LOCATIONS.items():
        if key in normalized or normalized in key:
            return {**value, "source": "known"}

    geocode_url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&addressdetails=1&countrycodes=in&q=" + urllib.parse.quote(query)
    try:
        request = urllib.request.Request(geocode_url, headers={"User-Agent": "SafeRoute-AI/1.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.load(response)
        if payload:
            hit = payload[0]
            return {
                "latitude": float(hit.get("lat", 12.9716)),
                "longitude": float(hit.get("lon", 77.5946)),
                "display_name": hit.get("display_name", query),
                "source": "nominatim",
            }
    except Exception:
        pass

    return {"latitude": 12.9716, "longitude": 77.5946, "display_name": "Bengaluru, Karnataka", "source": "fallback"}

@app.on_event("startup")
async def startup():
    global crime_df, density_grid, model_bundle

    # ── Load & process crime data ─────────────────────────────────────────────
    crime_df     = dp.load_and_clean(DATA_PATH)
    _, _clusters = dp.cluster_hotspots(crime_df)
    density_grid = dp.compute_density_grid(crime_df)
    ss.load_density_grid(density_grid)

    # ── Train / load ML model ─────────────────────────────────────────────────
    if os.path.exists(MODEL_PATH):
        model_bundle = rm.load_model(MODEL_PATH)
        print(f"✅ Loaded model: {model_bundle['model_name']}")
    else:
        print("Training ML model (first run)…")
        model_bundle = rm.train(DATA_PATH, MODEL_PATH)

    print("🚀 Namma Safe BLR API ready!")


# ─── Pydantic schemas ─────────────────────────────────────────────────────────
class RouteRequest(BaseModel):
    src_lat: float = Field(..., example=12.9716)
    src_lon: float = Field(..., example=77.5946)
    dst_lat: float = Field(..., example=12.9352)
    dst_lon: float = Field(..., example=77.6245)
    hour:    int   = Field(22, ge=0, le=23)
    algorithm: str = Field("astar", pattern="^(astar|dijkstra)$")

class RiskRequest(BaseModel):
    latitude:         float = Field(..., example=12.9716)
    longitude:        float = Field(..., example=77.5946)
    hour:             int   = Field(22, ge=0, le=23)
    lighting_score:   Optional[float] = None
    cctv_score:       Optional[float] = None
    crowd_density:    Optional[float] = None
    police_proximity: Optional[float] = None

class IncidentReport(BaseModel):
    latitude:    float
    longitude:   float
    description: str
    severity:    int = Field(5, ge=1, le=10)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Namma Safe BLR", "version": "1.0"}


@app.post("/find-safe-route", tags=["Navigation"])
def find_safe_route(req: RouteRequest):
    """Find the safest route between two points."""
    result = re.find_safe_route(
        req.src_lat, req.src_lon,
        req.dst_lat, req.dst_lon,
        hour      = req.hour,
        algorithm = req.algorithm,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/predict-risk", tags=["ML"])
def predict_risk(req: RiskRequest):
    """Predict crime risk level for a location using the ML model."""
    from data_processing import time_risk_factor

    time_risk = time_risk_factor(req.hour)
    crime_density = ss._nearest_density(req.latitude, req.longitude)

    features = {
        "severity_norm":     crime_density,
        "time_risk":         time_risk,
        "lighting_score":    req.lighting_score  if req.lighting_score  is not None else 0.5,
        "cctv_score":        req.cctv_score      if req.cctv_score      is not None else 0.4,
        "crowd_density":     req.crowd_density   if req.crowd_density   is not None else 0.5,
        "police_proximity":  req.police_proximity if req.police_proximity is not None else 0.5,
        "is_night":          1 if (req.hour >= 20 or req.hour < 6) else 0,
        "hour":              req.hour,
    }

    prediction = rm.predict_risk(model_bundle, features)
    safety     = ss.compute_safety_score(req.latitude, req.longitude, req.hour,
                                         req.lighting_score, req.cctv_score, req.crowd_density)

    return {**prediction, **safety, "features_used": features}


@app.get("/get-crime-heatmap", tags=["Visualization"])
def get_crime_heatmap(limit: int = 500):
    """Return crime density grid for heatmap rendering."""
    data = density_grid[:limit]
    return {"heatmap": data, "total_cells": len(density_grid)}


@app.get("/get-crime-points", tags=["Visualization"])
def get_crime_points(limit: int = 300):
    """Return raw crime records for marker rendering."""
    if crime_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    sample = crime_df.sample(min(limit, len(crime_df)), random_state=42)
    return {"crimes": sample[["latitude","longitude","crime_type","crime_severity","hour","area"]].to_dict("records")}


@app.get("/geocode", tags=["Geocoding"])
def geocode_endpoint(query: str):
    """Resolve a place name or coordinate string into latitude/longitude."""
    return geocode_query(query)


@app.post("/report-incident", tags=["Community"])
def report_incident(report: IncidentReport):
    """Crowd-sourced incident reporting."""
    entry = {
        "id":          len(incidents_log) + 1,
        "latitude":    report.latitude,
        "longitude":   report.longitude,
        "description": report.description,
        "severity":    report.severity,
        "timestamp":   datetime.utcnow().isoformat(),
    }
    incidents_log.append(entry)
    return {"status": "reported", "incident_id": entry["id"]}


@app.get("/get-incidents", tags=["Community"])
def get_incidents():
    """Fetch all crowd-reported incidents."""
    return {"incidents": incidents_log, "total": len(incidents_log)}


@app.get("/analytics/summary", tags=["Analytics"])
def analytics_summary():
    """High-level analytics summary."""
    if crime_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    by_area  = crime_df.groupby("area")["crime_type"].count().sort_values(ascending=False).head(10).to_dict()
    by_type  = crime_df["crime_type"].value_counts().to_dict()
    by_hour  = crime_df.groupby("hour")["crime_type"].count().to_dict()
    night_d  = crime_df[crime_df["is_night"]==1]["crime_type"].count()
    day_d    = crime_df[crime_df["is_night"]==0]["crime_type"].count()

    return {
        "total_records":    len(crime_df),
        "by_area":          by_area,
        "by_crime_type":    by_type,
        "by_hour":          {str(k): int(v) for k, v in by_hour.items()},
        "night_crimes":     int(night_d),
        "day_crimes":       int(day_d),
        "model_name":       model_bundle["model_name"] if model_bundle else "Not loaded",
        "model_accuracy":   round(model_bundle["test_accuracy"]*100, 2) if model_bundle else 0,
    }
