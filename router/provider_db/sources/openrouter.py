"""
OpenRouter API - fetch model catalog.
Returns list of canonical model IDs.
"""

import aiohttp
from typing import List
from ..model_mapper import model_mapper


class OpenRouterFetcher:
    API_URL = "https://openrouter.ai/api/v1/models"
    
    async def fetch(self, api_key: str = None) -> List[str]:
        """Fetch all model IDs from OpenRouter."""
        headers = {"User-Agent": "SmarterRouter/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
        
        model_ids = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if model_id:
                model_ids.append(model_id)
        
        print(f"OpenRouter: {len(model_ids)} models")
        return model_ids


async def fetch_openrouter_models(api_key: str = None) -> List[str]:
    return await OpenRouterFetcher().fetch(api_key)
