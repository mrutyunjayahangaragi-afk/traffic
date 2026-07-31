import unittest

from Backend.parking_service import build_parking_candidates, recommend_parking, build_walking_route, normalize_osm_parking_records


class ParkingServiceTests(unittest.TestCase):
    def test_build_parking_candidates_returns_structured_locations(self):
        candidates = build_parking_candidates(
            destination_lat=12.9352,
            destination_lon=77.6245,
            radius_m=800,
            hour=22,
        )
        self.assertTrue(len(candidates) >= 1)
        first = candidates[0]
        self.assertIn("name", first)
        self.assertIn("final_score", first)
        self.assertIn("walking_distance_m", first)

    def test_recommend_parking_returns_ranked_recommendations(self):
        candidates = build_parking_candidates(
            destination_lat=12.9352,
            destination_lon=77.6245,
            radius_m=800,
            hour=22,
        )
        recommendations = recommend_parking(candidates, destination_lat=12.9352, destination_lon=77.6245, hour=22)
        self.assertTrue(len(recommendations) >= 1)
        self.assertIn("reason", recommendations[0])
        self.assertGreaterEqual(recommendations[0]["final_score"], 0)

    def test_build_walking_route_returns_points(self):
        route = build_walking_route(12.9352, 77.6245, 12.9360, 77.6250, hour=22)
        self.assertTrue(len(route) >= 2)

    def test_normalize_osm_parking_records_returns_structured_fields(self):
        payload = {
            "elements": [
                {
                    "type": "node",
                    "lat": 12.9352,
                    "lon": 77.6245,
                    "tags": {
                        "name": "Park Plaza",
                        "amenity": "parking",
                        "capacity": "80",
                        "fee": "yes",
                        "covered": "yes",
                        "wheelchair": "yes"
                    }
                }
            ]
        }
        normalized = normalize_osm_parking_records(payload)
        self.assertEqual(normalized[0]["name"], "Park Plaza")
        self.assertEqual(normalized[0]["capacity"], 80)
        self.assertTrue(normalized[0]["wheelchair_accessible"])


if __name__ == "__main__":
    unittest.main()
