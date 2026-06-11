"""
test_agent.py
-------------

A small, dependency-free test suite for the lease agent. It uses only Python's
built-in `unittest` module.

Run it with:

    python -m unittest test_agent.py

To keep the tests fast and predictable, they do NOT read the real data files.
Instead each test passes a small, controlled inventory and policy set directly
into evaluate_request(...). This way the tests check the agent's LOGIC and never
break just because the inventory file changes.
"""

import unittest

from agent import evaluate_request, extract_request_details


# A tiny, controlled tower inventory (keyed by tower_id, exactly like tools.py
# produces). The values mirror the assignment's sample data.
TOWERS = {
    "TWR-101": {
        "tower_id": "TWR-101",
        "region": "DXB-North",
        "max_allowed_weight_kg": 500,
        "current_weight_kg": 460,
    },
    "TWR-104": {
        "tower_id": "TWR-104",
        "region": "DXB-North",
        "max_allowed_weight_kg": 600,
        "current_weight_kg": 595,
    },
    "TWR-102": {
        "tower_id": "TWR-102",
        "region": "SHJ-Coastal",
        "max_allowed_weight_kg": 300,
        "current_weight_kg": 120,
    },
}

# Controlled regional policies (same shape as tools.load_policies produces).
POLICIES = {
    "DXB-North": {"max_height_m": 45, "max_single_asset_weight_kg": None},
    "SHJ-Coastal": {"max_height_m": None, "max_single_asset_weight_kg": 25},
    "SHJ-South": {"max_height_m": None, "max_single_asset_weight_kg": 15},
}


class TestLeaseAgent(unittest.TestCase):
    """Each method below is one scenario the agent must handle."""

    def judge(self, text):
        """Helper: evaluate a request against our controlled fixtures."""
        return evaluate_request(text, towers_by_id=TOWERS, policies=POLICIES)

    # -- 1. The headline success case from the assignment -------------------
    def test_standard_approved_case(self):
        text = (
            "Operator Du wants to mount a 15kg 5G antenna at a height of "
            "40 meters on Tower TWR-101."
        )
        result = self.judge(text)
        self.assertEqual(result["status"], "APPROVED")
        # 460 + 15 = 475, which is <= 500.
        self.assertEqual(result["final_tower_weight_kg"], 475)
        self.assertEqual(result["checks"]["request_parse_check"], "PASSED")
        self.assertTrue(result["checks"]["tower_exists"])
        self.assertEqual(result["checks"]["weight_capacity_check"], "PASSED")
        self.assertEqual(result["checks"]["regional_height_check"], "PASSED")

    # -- 2. Tower not found -------------------------------------------------
    def test_tower_not_found(self):
        text = (
            "Operator Du wants to mount a 10kg radio at a height of 20 meters "
            "on Tower TWR-999."
        )
        result = self.judge(text)
        self.assertEqual(result["status"], "REJECTED")
        self.assertFalse(result["checks"]["tower_exists"])
        self.assertIn("not found", result["reason"])

    # -- 3. Tower weight capacity exceeded ----------------------------------
    def test_weight_capacity_exceeded(self):
        # TWR-104 is at 595/600; adding 20kg -> 615 > 600.
        text = (
            "Operator Du wants to mount a 20kg dish at a height of 30 meters "
            "on Tower TWR-104."
        )
        result = self.judge(text)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["checks"]["weight_capacity_check"], "FAILED")
        # Regional checks should not run after weight fails.
        self.assertEqual(result["checks"]["regional_height_check"], "NOT_RUN")

    # -- 4. Regional height limit exceeded ----------------------------------
    def test_regional_height_exceeded(self):
        # DXB-North caps height at 45m; 50m must fail.
        text = (
            "Operator Du wants to mount a 5kg sensor at a height of 50 meters "
            "on Tower TWR-101."
        )
        result = self.judge(text)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["checks"]["regional_height_check"], "FAILED")

    # -- 5. SHJ-Coastal single-asset weight limit exceeded ------------------
    def test_regional_single_asset_weight_exceeded(self):
        # SHJ-Coastal caps a single asset at 25kg; 30kg must fail.
        text = (
            "Operator Du wants to mount a 30kg 5G antenna at a height of "
            "15 meters on Tower TWR-102."
        )
        result = self.judge(text)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(
            result["checks"]["regional_single_asset_weight_check"], "FAILED"
        )

    # -- 6. Missing height should be rejected -------------------------------
    def test_missing_height_rejected(self):
        # No height anywhere in the sentence.
        text = "Operator Du wants to mount a 15kg 5G antenna on Tower TWR-101."
        result = self.judge(text)
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["checks"]["request_parse_check"], "FAILED")
        self.assertIsNone(result["requested_height_m"])

    # -- 7. Lowercase tower ID is normalized and still works ----------------
    def test_lowercase_tower_id(self):
        text = (
            "Operator Du wants to mount a 15kg 5G antenna at a height of "
            "40 meters on Tower twr-101."
        )
        result = self.judge(text)
        self.assertEqual(result["tower_id"], "TWR-101")  # normalized to uppercase
        self.assertEqual(result["status"], "APPROVED")

    # -- Bonus: extraction handles spacing and decimals ---------------------
    def test_extraction_variants(self):
        details = extract_request_details(
            "Operator Du wants to mount a 15.5 kg 5G antenna at a height of "
            "40m on Tower TWR-101."
        )
        self.assertEqual(details["requested_weight_kg"], 15.5)  # decimal kept as float
        self.assertEqual(details["requested_height_m"], 40)     # whole number kept as int
        self.assertEqual(details["tower_id"], "TWR-101")


if __name__ == "__main__":
    unittest.main()
