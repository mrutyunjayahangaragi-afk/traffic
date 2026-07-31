import os
import sys
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class ParkingRepository:
    """Lightweight repository abstraction for parking data persistence hooks."""

    def __init__(self) -> None:
        self._store: List[Dict[str, Any]] = []

    def save_parking(self, parking: Dict[str, Any]) -> Dict[str, Any]:
        parking = dict(parking)
        parking.setdefault("id", f"parking-{len(self._store)+1}")
        self._store.append(parking)
        return parking

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._store)
