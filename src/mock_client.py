import os
import json

try:
    from google.genai.types import GenerateContentConfig
except ImportError:
    # Fallback simulation of the GenAI type
    class GenerateContentConfig:
        def __init__(self, system_instruction=None):
            self.system_instruction = system_instruction

class MockTokenCountResponse:
    def __init__(self, tokens):
        self.total_tokens = tokens

class MockUsageMetadata:
    def __init__(self, prompt_tokens, candidate_tokens=None):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = candidate_tokens if candidate_tokens is not None else 0
        self.total_token_count = self.prompt_token_count + self.candidates_token_count

class MockResponse:
    def __init__(self, text, prompt_tokens, candidate_tokens=None):
        self.text = text
        # If only total tokens provided (old way), treat as prompt tokens for metadata
        self.usage_metadata = MockUsageMetadata(prompt_tokens, candidate_tokens)

class MockFile:
    def __init__(self, uri, mime_type):
        self.uri = uri
        self.mime_type = mime_type
        self.state = type('State', (), {'name': 'ACTIVE'})

def _get_sys_inst(config):
    """Helper to extract system instruction from dict or object."""
    if not config:
        return None
    if isinstance(config, dict):
        return config.get('system_instruction')
    return getattr(config, 'system_instruction', None)

def _estimate_tokens(contents, system_instruction=None):
    """
    Estimates tokens based on content type:
    - Text: 1 token per 4 characters
    - Image: 70 tokens (simplified)
    - Video: 280 tokens (simplified)
    """
    total = 0
    if system_instruction:
        total += _estimate_tokens(str(system_instruction))

    if contents is None:
        return total
    
    if isinstance(contents, str):
        total += len(contents) // 4 + 1
        return total
    
    if isinstance(contents, list):
        total += sum(_estimate_tokens(part) for part in contents)
        return total
    
    # Check for objects with mime_type (like MockFile or GenAI File)
    mime_type = getattr(contents, 'mime_type', None)
    if mime_type:
        if mime_type.startswith('image/'):
            total += 70
        elif mime_type.startswith('video/'):
            total += 280
        return total
            
    # Check for PIL Image or similar objects
    if hasattr(contents, 'size') and hasattr(contents, 'format'):
        total += 70
        return total
        
    # Fallback to string conversion
    total += len(str(contents)) // 4 + 1
    return total

class MockChat:
    def __init__(self, model, config=None):
        self.model = model
        self.config = config
        self.system_instruction = _get_sys_inst(config)
        self.history = []

    def get_history(self):
        return self.history

    def send_message(self, message, **kwargs):
        # Merge kwargs config if present
        config = kwargs.get('config', self.config)
        sys_inst = _get_sys_inst(config) or self.system_instruction
        
        input_tokens = _estimate_tokens(message, system_instruction=sys_inst)
        
        # JSON formatted response for the judge
        json_content = {
            "origin_analysis": {
                "prediction": "AI-Generated",
                "confidence_score": 0.85,
                "text_artifacts": [],
                "video_artifacts": ["Consistent frame flickering", "Static background"],
                "technical_reasoning": "The content exhibits high perplexity variance characteristic of generative models."
            },
            "social_performance": {
                "virality_score": 7,
                "performance_drivers": ["Controversial topic", "High engagement hooks"],
                "strategic_reasoning": "Leverages current trends to maximize algorithmic reach."
            },
            "distribution_strategy": {
                "target_audiences": ["Tech enthusiasts", "Journalists"],
                "resonance_factor": "Medium"
            },
            "metadata": {
                "analysis_summary": "Overall assessment suggests automated creation with minor human editing."
            }
        }
        text = f"```json\n{json.dumps(json_content, indent=2)}\n```"
        output_tokens = _estimate_tokens(text)
        
        self.history.append({"role": "user", "parts": [message]})
        self.history.append({"role": "model", "parts": [text]})
        
        return MockResponse(text, input_tokens, output_tokens)

class MockModels:
    def count_tokens(self, model, contents, config=None):
        sys_inst = _get_sys_inst(config)
        tokens = _estimate_tokens(contents, system_instruction=sys_inst)
        return MockTokenCountResponse(tokens)

    def generate_content(self, model, contents, **kwargs):
        config = kwargs.get('config')
        sys_inst = _get_sys_inst(config)
        
        input_tokens = _estimate_tokens(contents, system_instruction=sys_inst)
        
        json_content = {
            "origin_analysis": {
                "prediction": "Human-Generated",
                "confidence_score": 0.92,
                "text_artifacts": ["Personal anecdotes", "Emotional depth"],
                "video_artifacts": [],
                "technical_reasoning": "The content shows organic complexity and unique creative choices reflecting personal intent."
            },
            "social_performance": {
                "virality_score": 4,
                "performance_drivers": ["Authenticity", "Niche appeal"],
                "strategic_reasoning": "Focuses on community building rather than mass virality."
            },
            "distribution_strategy": {
                "target_audiences": ["Academic researchers", "History buffs"],
                "resonance_factor": "High within niche"
            },
            "metadata": {
                "analysis_summary": "Analysis confirms high probability of human authorship."
            }
        }
        text = f"```json\n{json.dumps(json_content, indent=2)}\n```"
        output_tokens = _estimate_tokens(text)
        
        return MockResponse(text, input_tokens, output_tokens)

class MockChats:
    def create(self, model, **kwargs):
        return MockChat(model, config=kwargs.get('config'))

class MockFiles:
    def upload(self, file, **kwargs):
        mime_type = "application/octet-stream"
        if isinstance(file, str):
            ext = os.path.splitext(file)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.webp']:
                mime_type = f"image/{ext[1:] if ext != '.jpg' else 'jpeg'}"
            elif ext in ['.mp4', '.mpeg', '.mov', '.avi']:
                mime_type = f"video/{ext[1:] if ext != '.avi' else 'x-msvideo'}"
        
        return MockFile(uri=f"mock://{file}", mime_type=mime_type)

    def get(self, name):
        # Default mock behavior
        return MockFile(uri=f"mock://{name}", mime_type="video/mp4")

class MockClient:
    def __init__(self, api_key=None):
        """
        Mock client that mimics the google.genai.Client interface.
        Accepts api_key for drop-in compatibility with main.py.
        """
        self.models = MockModels()
        self.chats = MockChats()
        self.files = MockFiles()
