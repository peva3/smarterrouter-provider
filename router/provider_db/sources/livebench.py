"""
LiveBench - fetch reasoning scores.
Primary source for reasoning_score (0-100).
"""

import aiohttp
from typing import Dict
from ..model_mapper import model_mapper


class LiveBenchFetcher:
    """Fetches reasoning benchmark from LiveBench."""
    
    API_URL = "https://livebench.ai/api/leaderboard"
    
    async def fetch(self) -> Dict[str, float]:
        """Return dict: model_id -> reasoning_score (0-100)."""
        scores = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        scores = self._parse(data)
                        if scores:
                            print(f"LiveBench: {len(scores)} reasoning scores")
                            return scores
        except Exception as e:
            pass
        
        # Try alternative URL
        alt_url = "https://livebench.ai/leaderboard/data"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(alt_url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        scores = self._parse(data)
                        if scores:
                            print(f"LiveBench: {len(scores)} reasoning scores (alt)")
                            return scores
        except Exception as e:
            pass
        
        print("LiveBench: failed to fetch")
        return {}
    
    def _parse(self, data) -> Dict[str, float]:
        scores = {}
        models = data.get("models", data.get("data", data.get("leaderboard", []))) if isinstance(data, dict) else data
        
        if not isinstance(models, list):
            return scores
        
        for item in models:
            name = item.get("model_name") or item.get("name") or item.get("model")
            score = item.get("score") or item.get("reasoning") or item.get("overall")
            if name and score:
                try:
                    s = float(score)
                    # Ensure 0-100
                    if s <= 1.0:
                        s *= 100
                    s = max(0.0, min(100.0, s))
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = s
                except (ValueError, TypeError):
                    continue
        return scores


async def fetch_livebench() -> Dict[str, float]:
    return await LiveBenchFetcher().fetch()
