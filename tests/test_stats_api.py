import unittest
from tests.helpers import BaseTestCase, get_json

class TestStatsApiContract(BaseTestCase):
    """
    Tests the shape of the /api/stats JSON payload as defined in docs/API_CONTRACTS.md.
    This test verifies that all required keys are present and correctly typed.
    """
    
    def test_stats_payload_shape(self):
        r = self.client.get("/api/stats")
        
        # Skip gracefully if the endpoint has not been merged by Member 3 yet
        if r.status_code == 404:
            self.skipTest("/api/stats endpoint not yet implemented.")

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content_type, "application/json")
        
        data = get_json(r)
        
        # 1. Totals object
        self.assertIn("totals", data)
        self.assertIsInstance(data["totals"], dict)
        totals = data["totals"]
        self.assertIn("posts", totals)
        self.assertIn("users", totals)
        self.assertIn("comments", totals)
        self.assertIn("tags", totals)
        
        # 2. Category counts array
        self.assertIn("category_counts", data)
        self.assertIsInstance(data["category_counts"], list)
        if len(data["category_counts"]) > 0:
            cat = data["category_counts"][0]
            self.assertIn("label", cat)
            self.assertIn("count", cat)
            
        # 3. 30-day trend array
        self.assertIn("trend_30", data)
        self.assertIsInstance(data["trend_30"], list)
        # Contract states missing days should be zero-filled up to 30 days
        self.assertEqual(len(data["trend_30"]), 30)
        
        if len(data["trend_30"]) > 0:
            trend = data["trend_30"][0]
            self.assertIn("date", trend)
            self.assertIn("count", trend)
            
        # 4. Top users array
        self.assertIn("top_users", data)
        self.assertIsInstance(data["top_users"], list)
        if len(data["top_users"]) > 0:
            top = data["top_users"][0]
            self.assertIn("username", top)
            self.assertIn("post_count", top)
            self.assertIn("total_likes", top)

if __name__ == "__main__":
    unittest.main()
