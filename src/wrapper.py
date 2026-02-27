from src.rate_limiter import RateLimiter

class LimitedChat:
    def __init__(self, chat, model, client, limiter):
        self._chat = chat
        self._model = model
        self._client = client
        self._limiter = limiter

    def send_message(self, message, **kwargs):
        # To count tokens for chat, we need the history + the new message
        history = self._chat.get_history()
        # We wrap the message in a temporary list for counting
        contents = [*history, message]
        
        try:
            token_count_resp = self._client.models.count_tokens(
                model=self._model,
                contents=contents,
                **kwargs
            )
            prompt_tokens = token_count_resp.total_tokens
        except Exception as e:
            print(f"Error counting tokens: {e}")
            prompt_tokens = 1000 # Conservative fallback

        self._limiter.wait_if_needed(self._model, prompt_tokens)
        
        response = self._chat.send_message(message, **kwargs)
        
        total_tokens = response.usage_metadata.total_token_count if response.usage_metadata else prompt_tokens
        self._limiter.update_usage(self._model, total_tokens)
        
        return response

class LimitedChats:
    def __init__(self, client, limiter):
        self._client = client
        self._limiter = limiter

    def create(self, model, **kwargs):
        chat = self._client.chats.create(model=model, **kwargs)
        return LimitedChat(chat, model, self._client, self._limiter)

class LimitedModels:
    def __init__(self, client, limiter):
        self._client = client
        self._limiter = limiter

    def generate_content(self, model, contents, **kwargs):
        try:
            token_count_resp = self._client.models.count_tokens(
                model=model,
                contents=contents,
                **kwargs
            )
            prompt_tokens = token_count_resp.total_tokens
        except Exception:
            prompt_tokens = len(str(contents)) // 4

        self._limiter.wait_if_needed(model, prompt_tokens)

        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            **kwargs
        )

        total_tokens = response.usage_metadata.total_token_count if response.usage_metadata else prompt_tokens
        self._limiter.update_usage(model, total_tokens)

        return response

class LimitedClient:
    def __init__(self, client, state_file="rate_limit_state.json", config_file="models_config.json", tier="free"):
        self._client = client
        self._limiter = RateLimiter(state_file, config_file, tier=tier)
        self.models = LimitedModels(client, self._limiter)
        self.chats = LimitedChats(client, self._limiter)

    def set_tier(self, tier):
        self._limiter.tier = tier

    @property
    def files(self):
        return self._client.files

