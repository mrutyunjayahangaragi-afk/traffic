import os
import sys
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class TrackingRepository:
    """In-memory repository for family tracking and alert state."""

    def __init__(self) -> None:
        self._contacts: List[Dict[str, Any]] = []
        self._sessions: List[Dict[str, Any]] = []
        self._locations: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []

    def add_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        contact = dict(contact)
        contact.setdefault("id", f"contact-{len(self._contacts)+1}")
        self._contacts.append(contact)
        return contact

    def get_contacts(self) -> List[Dict[str, Any]]:
        return list(self._contacts)

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        for contact in self._contacts:
            if contact.get("id") == contact_id:
                contact.update(updates)
                return contact
        raise KeyError(contact_id)

    def delete_contact(self, contact_id: str) -> bool:
        before = len(self._contacts)
        self._contacts = [c for c in self._contacts if c.get("id") != contact_id]
        return len(self._contacts) != before

    def add_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        session = dict(session)
        session.setdefault("id", f"session-{len(self._sessions)+1}")
        self._sessions.append(session)
        return session

    def update_session(self, token: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        for session in self._sessions:
            if session.get("tracking_token") == token:
                session.update(updates)
                return session
        raise KeyError(token)

    def get_sessions(self) -> List[Dict[str, Any]]:
        return list(self._sessions)

    def add_location(self, location: Dict[str, Any]) -> Dict[str, Any]:
        location = dict(location)
        self._locations.append(location)
        return location

    def get_locations(self, token: str) -> List[Dict[str, Any]]:
        return [loc for loc in self._locations if loc.get("tracking_token") == token]

    def add_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        alert = dict(alert)
        self._alerts.append(alert)
        return alert

    def get_alerts(self, token: str) -> List[Dict[str, Any]]:
        return [alert for alert in self._alerts if alert.get("tracking_token") == token]
