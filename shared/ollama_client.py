"""
Ollama LLM Client - Handles communication with local Ollama instance
Supports model listing, generation, and streaming
"""
import requests
import json
from shared.settings import OLLAMA_HOST, DEFAULT_MODEL, FALLBACK_MODELS

class OllamaClient:
    """
    Client for interacting with Ollama API.
    Automatically detects available models and supports dynamic model switching.
    """

    def __init__(self, host=None, model=None):
        self.host = host or OLLAMA_HOST
        self.model = model or DEFAULT_MODEL
        self.available_models = []
        self._refresh_models()

    def _refresh_models(self):
        """Fetch list of installed models from Ollama"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                self.available_models = [m["name"] for m in models]
            else:
                self.available_models = FALLBACK_MODELS.copy()
        except Exception:
            self.available_models = FALLBACK_MODELS.copy()

    def get_models(self):
        """Return list of available models"""
        self._refresh_models()
        return self.available_models if self.available_models else FALLBACK_MODELS

    def set_model(self, model_name):
        """Switch to a different model"""
        self.model = model_name

    def generate(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        """
        Generate text using the selected model.

        Args:
            prompt: The user prompt
            system: System prompt/instructions
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text string
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if system:
            payload["system"] = system

        try:
            resp = requests.post(
                f"{self.host}/api/generate", 
                json=payload, 
                #timeout=120
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return f"[Error: HTTP {resp.status_code}]"
        except requests.exceptions.ConnectionError:
            return "[Error: Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434]"
        except Exception as e:
            return f"[Error: {str(e)}]"

    def check_connection(self):
        """Check if Ollama is reachable"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=3)
            return resp.status_code == 200
        except:
            return False
