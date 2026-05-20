"""
Product Analysis Agent — Phase 4
=================================
Sends each product to the local Ollama LLM (Qwen2.5:7b or Mistral 7B).
Parses back JSON with demand_score, competition_score,
profit_estimate, and a written verdict.

Completely free — runs 100% offline using Ollama.
"""
import json
import requests
from typing import List, Optional, Callable
from producthunter.models.product import Product


OLLAMA_HOST = "http://localhost:11434"


class AnalysisAgent:
    """
    Analyses products using a local Ollama LLM.

    Usage:
        agent = AnalysisAgent(model="qwen2.5:7b")
        product = agent.analyse(product)
    """

    def __init__(self, model: str = "qwen2.5:7b",
                 host: str = OLLAMA_HOST):
        self.model = model
        self.host = host

    # ------------------------------------------------------------------ #
    # Connection check                                                     #
    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        """Check if Ollama is running and model is loaded."""
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------ #
    # Single product analysis                                              #
    # ------------------------------------------------------------------ #
    def analyse(self, product: Product) -> Product:
        """
        Run AI analysis on a single product.
        Fills: demand_score, competition_score, profit_estimate, ai_verdict.
        Returns the same product with fields populated.
        """
        prompt = self._build_prompt(product)
        raw = self._call_ollama(prompt)

        if not raw:
            product.ai_verdict = "Analysis failed — Ollama not responding."
            return product

        parsed = self._parse_response(raw)
        product.demand_score      = parsed.get("demand_score", 0.0)
        product.competition_score = parsed.get("competition_score", 50.0)
        product.profit_estimate   = parsed.get("profit_estimate_pkr", 0.0)
        product.ai_verdict        = parsed.get("verdict", raw[:300])
        return product

    # ------------------------------------------------------------------ #
    # Batch analysis                                                       #
    # ------------------------------------------------------------------ #
    def analyse_batch(self, products: List[Product],
                      progress_cb: Optional[Callable] = None) -> List[Product]:
        """
        Analyse a list of products one by one.
        Calls progress_cb(current, total) after each product.
        """
        total = len(products)
        for i, p in enumerate(products):
            products[i] = self.analyse(p)
            if progress_cb:
                progress_cb(i + 1, total)
        return products

    # ------------------------------------------------------------------ #
    # Ollama API call                                                      #
    # ------------------------------------------------------------------ #
    def _call_ollama(self, prompt: str) -> str:
        """Send prompt to Ollama and return the raw text response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,    # Lower = more consistent JSON output
                "num_predict": 400,
            }
        }
        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except requests.exceptions.ConnectionError:
            print("[AnalysisAgent] Ollama is not running.")
        except requests.exceptions.Timeout:
            print("[AnalysisAgent] Ollama timed out.")
        except Exception as e:
            print(f"[AnalysisAgent] Error: {e}")
        return ""

    # ------------------------------------------------------------------ #
    # Prompt builder                                                       #
    # ------------------------------------------------------------------ #
    def _build_prompt(self, product: Product) -> str:
        """
        Build a structured prompt that asks the LLM to return only JSON.
        The strict format makes it easy to parse reliably.
        """
        return f"""You are an expert e-commerce consultant specialising in the Pakistani market.

Analyse this product and return ONLY a valid JSON object — no explanation, no markdown, no extra text.

JSON format:
{{
  "demand_score": <integer 0-100>,
  "competition_score": <integer 0-100>,
  "profit_estimate_pkr": <integer>,
  "verdict": "<2-3 sentences explaining demand, competition, and why it suits Pakistan>"
}}

Product details:
- Title: {product.title}
- Category: {product.category}
- Price: {product.currency} {product.price:.0f}
- Rating: {product.rating}/5
- Reviews: {product.reviews}
- Sold/Engagement: {product.sold_count}
- Trend Score (Google): {product.trend_score:.1f}/100
- Source: {product.source}

Rules:
- demand_score: how much demand exists in Pakistan (0=none, 100=viral)
- competition_score: how saturated the market is (0=blue ocean, 100=overcrowded)
- profit_estimate_pkr: realistic monthly profit in Pakistani Rupees for a small seller
- Consider Pakistani income levels, mobile-first shopping, and COD preference
"""

    # ------------------------------------------------------------------ #
    # Response parser                                                      #
    # ------------------------------------------------------------------ #
    def _parse_response(self, raw: str) -> dict:
        """
        Extract JSON from LLM response.
        LLMs sometimes wrap JSON in ```json ... ``` — we handle that.
        """
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    cleaned = part
                    break

        # Find first { ... } block
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return {}

        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError as e:
            print(f"[AnalysisAgent] JSON parse error: {e}")
            return {}