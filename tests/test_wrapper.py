import unittest
import os
import json
import tempfile
from src.wrapper import LimitedClient
from src.mock_client import MockClient
from google.genai.types import GenerateContentConfig

class TestWrapper(unittest.TestCase):
    def setUp(self):
        # Setup config
        self.config_fd, self.config_path = tempfile.mkstemp(suffix=".json")
        self.config = {
            "free": {
                "gemini-2.5-flash": {
                    "rpm": 5,
                    "tpm": 250000,
                    "rpd": 20
                }
            },
            "tier1": {
                "gemini-2.5-flash": {
                    "rpm": 1000,
                    "tpm": 4000000,
                    "rpd": 10000
                }
            }
        }
        with os.fdopen(self.config_fd, 'w') as f:
            json.dump(self.config, f)
        
        self.state_fd, self.state_path = tempfile.mkstemp(suffix=".json")
        os.close(self.state_fd)
        
        self.mock_base_client = MockClient(api_key="test-key")
        self.client = LimitedClient(
            self.mock_base_client, 
            state_file=self.state_path, 
            config_file=self.config_path,
            tier="free"
        )

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.state_path):
            os.remove(self.state_path)

    def test_set_tier(self):
        self.assertEqual(self.client._limiter.tier, "free")
        self.client.set_tier("tier1")
        self.assertEqual(self.client._limiter.tier, "tier1")

    def test_generate_content(self):
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello"
        )
        self.assertIn("origin_analysis", response.text)
        self.assertIn("prediction", response.text)
        
        # Verify state updated
        with open(self.state_path, 'r') as f:
            state = json.load(f)
        self.assertEqual(len(state["gemini-2.5-flash"]), 1)

    def test_chat(self):
        chat = self.client.chats.create(model="gemini-2.5-flash")
        response = chat.send_message("How are you?")
        self.assertIn("origin_analysis", response.text)
        self.assertIn("prediction", response.text)

    def test_system_instruction_propagation(self):
        sys_inst = "Act as an evaluator"
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello",
            config=GenerateContentConfig(system_instruction=sys_inst)
        )
        # We no longer expect sys_inst to leak into response.text
        # "Hello" is 2 tokens, sys_inst is 19 chars -> 4+1=5 tokens. Total should be 7.
        self.assertEqual(response.usage_metadata.prompt_token_count, 7)

if __name__ == "__main__":
    unittest.main()
