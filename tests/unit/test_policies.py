import unittest

from coldcraft.domain import policies


class PolicyValidationTests(unittest.TestCase):
    def test_rejects_daily_limit_above_constitution(self):
        with self.assertRaises(ValueError):
            policies.validate_policy_overrides(daily_send_limit=25)

    def test_allows_stricter_daily_limit(self):
        policies.validate_policy_overrides(daily_send_limit=10)

    def test_clamp_policy_value(self):
        self.assertEqual(policies.clamp_policy_value("daily_send_limit", 100), 20)
        self.assertEqual(policies.clamp_policy_value("subject_max_chars", 80), 50)


if __name__ == "__main__":
    unittest.main()