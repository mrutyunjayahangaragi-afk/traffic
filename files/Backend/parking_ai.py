from typing import List, Dict, Any


def summarize_recommendation(candidate: Dict[str, Any]) -> str:
    return (
        f"{candidate['name']} — Safety {candidate['parking_safety_score']}/100, "
        f"Availability {candidate['availability_percentage']}%, Walk {candidate['walking_distance_m']}m"
    )


def build_alerts(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts = []
    if candidates:
        best = candidates[0]
        alerts.append({"type": "parking", "message": f"AI selected {best['name']} as the safest nearby option."})
        if best["availability_percentage"] < 40:
            alerts.append({"type": "warning", "message": "Selected parking is nearly full."})
    return alerts
