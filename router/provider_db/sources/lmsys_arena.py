"""
LMSYS Chatbot Arena - fetch ELO ratings.
Primary source for elo_rating field.
"""

import aiohttp
from typing import Dict
from ..model_mapper import model_mapper


FALLBACK_ELO = {
    "openai/gpt-4": 1280,
    "openai/gpt-4-turbo": 1295,
    "openai/gpt-4o": 1340,
    "openai/gpt-4o-mini": 1280,
    "openai/gpt-3.5-turbo": 1100,
    "anthropic/claude-3-opus": 1350,
    "anthropic/claude-3-sonnet": 1320,
    "anthropic/claude-3-5-sonnet": 1380,
    "anthropic/claude-3-5-haiku": 1260,
    "google/gemini-pro": 1300,
    "google/gemini-pro-1.5": 1320,
    "google/gemini-flash": 1250,
    "google/gemini-flash-1.5": 1270,
    "meta/llama-3-70b-instruct": 1250,
    "meta/llama-3-8b-instruct": 1180,
    "meta/llama-3.1-70b-instruct": 1280,
    "meta/llama-3.1-405b-instruct": 1320,
    "mistralai/mistral-large": 1280,
    "mistralai/mistral-medium": 1200,
    "mistralai/mistral-small": 1150,
    "mistralai/mixtral-8x7b": 1200,
    "cohere/command-r-plus": 1200,
    "cohere/command-r": 1150,
    "ai21/jamba-1.5-large": 1220,
    "ai21/jamba-1.5-mini": 1180,
    "xai/grok-beta": 1240,
    "nvidia/nemotron-70b": 1210,
    "deepseek/deepseek-chat": 1260,
    "deepseek/deepseek-coder": 1240,
    "openchat/openchat-7b": 1120,
    "together/llama-3-sonar-large": 1230,
}


class LMSYSFetcher:
    """Fetches ELO from LMSYS Chatbot Arena leaderboard."""
    
    # HuggingFace Spaces raw file
    JSON_URL = "https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard/raw/main/elo_ratings.json"
    CSV_URL = "https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard/resolve/main/leaderboard.csv"
    
    async def fetch(self) -> Dict[str, int]:
        """Return dict: model_id -> elo_rating (raw integer)."""
        scores = {}
        
        # Try JSON first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.JSON_URL, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        scores = self._parse_json(data)
                        if scores:
                            print(f"LMSYS Arena: {len(scores)} ELO ratings (JSON)")
                            return scores
        except Exception as e:
            pass
        
        # Fallback CSV
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.CSV_URL, timeout=30) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        scores = self._parse_csv(text)
                        if scores:
                            print(f"LMSYS Arena: {len(scores)} ELO ratings (CSV)")
                            return scores
        except Exception as e:
            pass
        
        print("LMSYS Arena: failed to fetch")
        return {}
    
    def _parse_json(self, data) -> Dict[str, int]:
        scores = {}
        models = data.get("models", data) if isinstance(data, dict) else data
        for item in (models if isinstance(models, list) else []):
            name = item.get("model_name") or item.get("name") or item.get("model")
            elo = item.get("elo") or item.get("rating")
            if name and elo:
                try:
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = int(float(elo))
                except (ValueError, TypeError):
                    continue
        return scores
    
    def _parse_csv(self, text: str) -> Dict[str, int]:
        scores = {}
        lines = text.strip().split("\n")[:100]  # Limit to top 100
        if len(lines) < 2:
            return scores
        
        headers = [h.lower() for h in lines[0].split(",")]
        name_idx = next((i for i, h in enumerate(headers) if "model" in h), 0)
        elo_idx = next((i for i, h in enumerate(headers) if "elo" in h or "rating" in h), 1)
        
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) > max(name_idx, elo_idx):
                name = parts[name_idx].strip(' "')
                try:
                    elo = int(float(parts[elo_idx]))
                    canonical = model_mapper.to_canonical(name)
                    if canonical:
                        scores[canonical] = elo
                except (ValueError, IndexError):
                    continue
        return scores


async def fetch_lmsys_arena() -> Dict[str, int]:
    scores = await LMSYSFetcher().fetch()
    if not scores:
        print("LMSYS Arena: using fallback ELO data")
        scores = dict(FALLBACK_ELO)
    return scores
