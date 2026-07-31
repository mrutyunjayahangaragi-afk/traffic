import os
import sys
import uuid
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class TrackingService:
    """Service layer for family tracking session lifecycle and shareable tokens."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def create_contact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.add_contact(payload)

    def list_contacts(self) -> List[Dict[str, Any]]:
        return self.repository.get_contacts()

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.update_contact(contact_id, updates)

    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        return {"deleted": self.repository.delete_contact(contact_id)}

    def start_tracking(self, user_id: str, destination: str = "") -> Dict[str, Any]:
        token = uuid.uuid4().hex
        session = {
            "user_id": user_id,
            "tracking_token": token,
            "session_status": "active",
            "destination": destination,
            "eta": 20,
            "safety_score": 94,
        }
        return self.repository.add_session(session)

    def stop_tracking(self, token: str) -> Dict[str, Any]:
        return self.repository.update_session(token, {"session_status": "stopped"})

    def share_tracking(self, token: str) -> Dict[str, Any]:
        return {"tracking_token": token, "share_url": f"/tracking/live/{token}"}

    def add_location(self, token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        location = {"tracking_token": token, **payload}
        return self.repository.add_location(location)

    def get_live_state(self, token: str) -> Dict[str, Any]:
        session = next((s for s in self.repository.get_sessions() if s.get("tracking_token") == token), None)
        return {
            "tracking_token": token,
            "session": session,
            "locations": self.repository.get_locations(token),
            "alerts": self.repository.get_alerts(token),
        }

    def add_alert(self, token: str, alert_type: str, message: str) -> Dict[str, Any]:
        return self.repository.add_alert({"tracking_token": token, "alert_type": alert_type, "message": message})

    def get_history(self) -> List[Dict[str, Any]]:
        return self.repository.get_sessions()
