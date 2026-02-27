import unittest
from src.parser import extract_json, sanitize_evaluation

class TestParser(unittest.TestCase):

    def test_extract_json_with_backticks(self):
        text = """Here is the result: ```json
{"key": "value"}
``` hope it helps!"""
        result = extract_json(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_no_backticks(self):
        text = 'Just the object: {"key": "value"}'
        result = extract_json(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_invalid(self):
        text = "Not a json at all"
        result = extract_json(text)
        self.assertIsNone(result)

    def test_sanitize_evaluation_full_match(self):
        raw_data = {
            "origin_analysis": {
                "prediction": "AI-Generated",
                "confidence_score": 0.95,
                "text_artifacts": ["A", "B"],
                "video_artifacts": [],
                "technical_reasoning": "Reason"
            },
            "social_performance": {
                "virality_score": 8,
                "performance_drivers": ["X"],
                "strategic_reasoning": "Strategy"
            },
            "distribution_strategy": {
                "target_audiences": ["Y"],
                "resonance_factor": "High"
            },
            "metadata": {
                "analysis_summary": "Summary"
            }
        }
        sanitized = sanitize_evaluation(raw_data)
        self.assertEqual(sanitized["origin_analysis"]["prediction"], "AI-Generated")
        self.assertEqual(sanitized["origin_analysis"]["confidence_score"], 0.95)

    def test_sanitize_evaluation_missing_fields(self):
        # Missing origin_analysis section entirely
        raw_data = {
            "metadata": {"analysis_summary": "Summary"}
        }
        sanitized = sanitize_evaluation(raw_data)
        self.assertEqual(sanitized["origin_analysis"]["prediction"], "[Missing]")
        self.assertEqual(sanitized["metadata"]["analysis_summary"], "Summary")

    def test_sanitize_evaluation_incorrect_types(self):
        raw_data = {
            "origin_analysis": {
                "prediction": ["AI-Generated"], # Should be str, got list
                "confidence_score": "High",     # Should be float/int, got str
                "text_artifacts": "None",       # Should be list, got str
                "video_artifacts": [],
                "technical_reasoning": "Reason"
            }
        }
        sanitized = sanitize_evaluation(raw_data)
        # Verify coercion to string for mismatched types
        self.assertEqual(sanitized["origin_analysis"]["prediction"], "['AI-Generated']")
        self.assertEqual(sanitized["origin_analysis"]["confidence_score"], "High")
        self.assertEqual(sanitized["origin_analysis"]["text_artifacts"], "None")

    def test_sanitize_evaluation_extra_fields(self):
        raw_data = {
            "metadata": {
                "analysis_summary": "Summary",
                "extra_field": "Ignore me"
            }
        }
        sanitized = sanitize_evaluation(raw_data)
        self.assertNotIn("extra_field", sanitized["metadata"])

if __name__ == "__main__":
    unittest.main()
