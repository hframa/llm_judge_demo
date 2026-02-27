import unittest
import os
import json
import time
import tempfile
from unittest.mock import patch
from src.rate_limiter import RateLimiter

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.config_fd, self.config_path = tempfile.mkstemp(suffix=".json")
        self.config = {
            "free": {
                "test-model": {
                    "rpm": 2,
                    "tpm": 100,
                    "rpd": 5
                }
            },
            "tier1": {
                "test-model": {
                    "rpm": 10,
                    "tpm": 1000,
                    "rpd": 100
                }
            }
        }
        with os.fdopen(self.config_fd, 'w') as f:
            json.dump(self.config, f)
        
        self.state_fd, self.state_path = tempfile.mkstemp(suffix=".json")
        os.close(self.state_fd)
        
        self.limiter = RateLimiter(state_file=self.state_path, config_file=self.config_path, tier="free")

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.state_path):
            os.remove(self.state_path)

    def test_tier_switching(self):
        self.assertEqual(self.limiter.limits["test-model"]["rpm"], 2)
        self.limiter.tier = "tier1"
        self.assertEqual(self.limiter.limits["test-model"]["rpm"], 10)

    def test_update_usage(self):
        self.limiter.update_usage("test-model", 10)
        with open(self.state_path, 'r') as f:
            state = json.load(f)
        self.assertEqual(len(state["test-model"]), 1)
        self.assertEqual(state["test-model"][0]["tokens"], 10)

    @patch('time.sleep')
    @patch('time.time')
    def test_rpm_limit_trigger(self, mock_time, mock_sleep):
        # Set constant time
        now = 1000.0
        mock_time.return_value = now
        
        # RPM is 2. Add 2 requests.
        self.limiter.update_usage("test-model", 1)
        self.limiter.update_usage("test-model", 1)
        
        # Next call should trigger sleep
        # We need a side effect for mock_time to break the while True loop in wait_if_needed
        # The first call to wait_if_needed will see 2 requests and sleep.
        # We'll make the second check see a much later time.
        mock_time.side_effect = [now, now, now + 61, now + 61]
        
        self.limiter.wait_if_needed("test-model", 1)
        
        mock_sleep.assert_called()
        self.assertGreater(mock_sleep.call_args[0][0], 0)

    @patch('time.sleep')
    @patch('time.time')
    def test_tpm_limit_trigger(self, mock_time, mock_sleep):
        now = 1000.0
        mock_time.return_value = now
        
        # TPM is 100. Add request with 90 tokens.
        self.limiter.update_usage("test-model", 90)
        
        # Next request of 20 tokens should exceed 100
        mock_time.side_effect = [now, now, now + 61, now + 61]
        
        self.limiter.wait_if_needed("test-model", 20)
        
        mock_sleep.assert_called()

    def test_prompt_exceeds_tpm(self):
        """Test that prompt_tokens > tpm raises ValueError when history is empty."""
        # TPM is 100. Request 110 tokens.
        with self.assertRaises(ValueError) as cm:
            self.limiter.wait_if_needed("test-model", 110)
        
        self.assertIn("exceed model TPM limit", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
