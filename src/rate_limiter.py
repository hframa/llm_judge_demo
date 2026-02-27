import json
import os
import time
import fcntl
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, state_file="rate_limit_state.json", config_file="models_config.json", tier="free"):
        self.state_file = state_file
        self.config_file = config_file
        self.all_limits = self._load_config()
        self.tier = tier
        self._ensure_state_file()

    @property
    def limits(self):
        return self.all_limits.get(self.tier, {})

    def _load_config(self):
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def _ensure_state_file(self):
        if not os.path.exists(self.state_file):
            with open(self.state_file, 'w') as f:
                json.dump({}, f)

    def _get_state(self, lock_file):
        try:
            lock_file.seek(0)
            data = lock_file.read()
            if not data:
                return {}
            return json.loads(data)
        except json.JSONDecodeError:
            return {}

    def _save_state(self, lock_file, state):
        lock_file.seek(0)
        lock_file.truncate()
        json.dump(state, lock_file, indent=2)

    def _clean_history(self, history):
        now = time.time()
        one_day_ago = now - 86400
        return [entry for entry in history if entry['timestamp'] > one_day_ago]

    def wait_if_needed(self, model, prompt_tokens):
        if model not in self.limits:
            print(f"Warning: No limits configured for model {model}. Proceeding without rate limiting.")
            return

        limit = self.limits[model]
        
        while True:
            with open(self.state_file, 'r+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    state = self._get_state(f)
                    history = state.get(model, [])
                    history = self._clean_history(history)
                    state[model] = history
                    self._save_state(f, state)

                    now = time.time()
                    one_minute_ago = now - 60
                    
                    # RPM check
                    recent_requests = [e for e in history if e['timestamp'] > one_minute_ago]
                    if len(recent_requests) >= limit['rpm']:
                        wait_time = 60 - (now - recent_requests[0]['timestamp']) + 0.1
                        print(f"RPM limit reached for {model}. Waiting {wait_time:.2f}s...")
                        time.sleep(max(0, wait_time))
                        continue

                    # TPM check
                    recent_tokens = sum(e['tokens'] for e in recent_requests)
                    if recent_tokens + prompt_tokens > limit['tpm']:
                        if not recent_requests:
                            raise ValueError(f"Prompt tokens ({prompt_tokens}) exceed model TPM limit ({limit['tpm']}) for {model}")
                        
                        # This is a bit simplistic; we wait until the oldest request in the window expires
                        wait_time = 60 - (now - recent_requests[0]['timestamp']) + 0.1
                        print(f"TPM limit reached for {model}. Waiting {wait_time:.2f}s...")
                        time.sleep(max(0, wait_time))
                        continue

                    # RPD check
                    if len(history) >= limit['rpd']:
                        wait_time = 86400 - (now - history[0]['timestamp']) + 1
                        print(f"RPD limit reached for {model}. Waiting {wait_time:.2f}s...")
                        time.sleep(max(0, wait_time))
                        continue

                    # If we got here, we are within limits
                    break
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)

    def update_usage(self, model, tokens):
        if model not in self.limits:
            return

        with open(self.state_file, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                state = self._get_state(f)
                history = state.get(model, [])
                history.append({
                    'timestamp': time.time(),
                    'tokens': tokens
                })
                state[model] = self._clean_history(history)
                self._save_state(f, state)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
