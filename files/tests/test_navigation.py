import unittest

from Backend.navigation_service import build_navigation_payload, generate_turn_instructions


class NavigationServiceTests(unittest.TestCase):
    def test_build_navigation_payload_includes_scores_and_eta(self):
        route = {
            "coordinates": [[12.97, 77.59], [12.98, 77.60], [12.99, 77.61]],
            "distance_km": 3.2,
            "total_risk_score": 0.42,
            "risk_level": "MEDIUM",
            "algorithm": "astar",
        }
        payload = build_navigation_payload(route, hour=22)
        self.assertEqual(payload["route_type"], "safest")
        self.assertGreater(payload["eta_minutes"], 0)
        self.assertIn("final_ai_score", payload)
        self.assertIn("instructions", payload)

    def test_generate_turn_instructions_returns_turn_text(self):
        coords = [(12.97, 77.59), (12.972, 77.595), (12.974, 77.6)]
        instructions = generate_turn_instructions(coords, 0)
        self.assertTrue(instructions["text"].startswith(("Turn", "Continue", "Destination")))


if __name__ == "__main__":
    unittest.main()
