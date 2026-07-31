from typing import Any, Dict, List


class FamilyService:
    """Thin service for family contact management."""

    def __init__(self, repository) -> None:
        self.repository = repository

    def add_contact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.add_contact(payload)

    def list_contacts(self) -> List[Dict[str, Any]]:
        return self.repository.get_contacts()

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.update_contact(contact_id, updates)

    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        return self.repository.delete_contact(contact_id)
