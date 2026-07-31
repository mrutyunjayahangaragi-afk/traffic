import unittest

from Backend.tracking_repository import TrackingRepository
from Backend.tracking_service import TrackingService


class TrackingServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = TrackingRepository()
        self.service = TrackingService(self.repo)

    def test_contact_and_tracking_lifecycle(self):
        contact = self.service.create_contact({"name": "Asha", "phone": "9999999999", "relationship": "Mother"})
        self.assertEqual(contact["name"], "Asha")

        session = self.service.start_tracking("user-1", destination="Koramangala")
        self.assertEqual(session["session_status"], "active")
        self.assertIn("tracking_token", session)

        shared = self.service.share_tracking(session["tracking_token"])
        self.assertIn("/tracking/live/", shared["share_url"])

        self.service.add_location(session["tracking_token"], {"lat": 12.9716, "lon": 77.5946})
        self.service.add_alert(session["tracking_token"], "safety", "Reached safe zone")

        live_state = self.service.get_live_state(session["tracking_token"])
        self.assertEqual(live_state["session"]["session_status"], "active")
        self.assertEqual(len(live_state["locations"]), 1)
        self.assertEqual(len(live_state["alerts"]), 1)

        stopped = self.service.stop_tracking(session["tracking_token"])
        self.assertEqual(stopped["session_status"], "stopped")


if __name__ == "__main__":
    unittest.main()
