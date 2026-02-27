import unittest
from google.genai.types import GenerateContentConfig
from src.mock_client import MockClient

class TestMockClientMultimodal(unittest.TestCase):
    def setUp(self):
        self.client = MockClient(api_key="test-key")

    def test_text_token_estimation(self):
        # "Hello" is 5 chars -> 1 token + 1 = 2 tokens (based on current //4 + 1 logic)
        res = self.client.models.count_tokens(model="mock", contents="Hello")
        self.assertEqual(res.total_tokens, 2)

    def test_image_token_estimation(self):
        image = self.client.files.upload(file="test.png")
        res = self.client.models.count_tokens(model="mock", contents=image)
        self.assertEqual(res.total_tokens, 70)

    def test_video_token_estimation(self):
        video = self.client.files.upload(file="test.mp4")
        res = self.client.models.count_tokens(model="mock", contents=video)
        self.assertEqual(res.total_tokens, 280)

    def test_mixed_content_estimation(self):
        image = self.client.files.upload(file="test.png")
        prompt = "Describe this image" # 19 chars -> 4 + 1 = 5 tokens
        res = self.client.models.count_tokens(model="mock", contents=[prompt, image])
        # 5 (text) + 70 (image) = 75
        self.assertEqual(res.total_tokens, 75)

    def test_generate_content_usage_metadata(self):
        image = self.client.files.upload(file="test.png")
        response = self.client.models.generate_content(
            model="mock", 
            contents=["Check this", image] # "Check this" is 10 chars -> 2 + 1 = 3 tokens. Total input = 73
        )
        self.assertEqual(response.usage_metadata.prompt_token_count, 73)
        self.assertGreater(response.usage_metadata.candidates_token_count, 0)
        self.assertEqual(
            response.usage_metadata.total_token_count, 
            response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count
        )

    def test_system_instruction_token_estimation(self):
        # "Hello" -> 2 tokens
        # System instruction: "Be helpful" -> 10 chars -> 2 + 1 = 3 tokens
        # Total should be 5 tokens
        res = self.client.models.count_tokens(
            model="mock", 
            contents="Hello",
            config=GenerateContentConfig(system_instruction="Be helpful")
        )
        self.assertEqual(res.total_tokens, 5)

if __name__ == "__main__":
    unittest.main()
