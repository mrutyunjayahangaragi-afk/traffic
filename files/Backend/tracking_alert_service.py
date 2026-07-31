from typing import Any, Dict, List


class TrackingAlertService:
    """Generates escalation-ready alerts for tracking sessions."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def create_alert(self, token: str, severity: str, message: str) -> Dict[str, Any]:
        return self.repository.add_alert({
            "tracking_token": token,
            "severity": severity,
            "message": message,
            "created_at": "now",
        })

    def list_alerts(self, token: str) -> List[Dict[str, Any]]:
        return self.repository.get_alerts(token)
