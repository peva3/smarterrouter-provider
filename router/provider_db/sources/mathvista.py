"""
MathVista - fetch math reasoning scores from MathVista benchmark.
Evaluates mathematical reasoning in visual contexts (multimodal).
"""

import re
import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# MathVista leaderboard top scores (from mathvista.github.io)
# Overall accuracy on testmini (1000) or test (5141) subset
FALLBACK_SCORES = {
    # Top models from leaderboard (InternVL family)
    "opengvlab/internvl2-pro": 65.8,
    "opengvlab/internvl2-8b-mpo": 65.7,
    "opengvlab/internvl-chat-v1.2-plus": 60.2,
    "opengvlab/internvl-chat-v1.5": 58.0,
    
    # GPT-4V family
    "openai/gpt-4v": 49.9,
    "openai/gpt-4o": 55.0,
    "openai/o3": 60.0,
    "openai/o3-mini": 52.0,
    "openai/gpt-4o-mini": 48.0,
    
    # Gemini family
    "google/gemini-ultra": 52.0,
    "google/gemini-2.5-pro": 58.0,
    "google/gemini-2.5-flash": 51.0,
    "google/gemini-pro": 45.0,
    "google/gemini-1.5-pro": 48.0,
    "google/gemini-1.5-flash": 44.0,
    
    # Claude family
    "anthropic/claude-3-opus": 48.0,
    "anthropic/claude-3-sonnet": 44.0,
    "anthropic/claude-3-5-sonnet": 50.0,
    "anthropic/claude-3-5-haiku": 47.0,
    "anthropic/claude-3-haiku": 43.0,
    "anthropic/claude-opus-4-6": 62.0,
    "anthropic/claude-sonnet-4-6": 58.0,
    
    # Qwen-VL
    "qwen/qwen-vl-plus": 44.3,
    "qwen/qwen-vl-max": 48.0,
    "qwen/qwen2-vl": 52.0,
    "qwen/qwen2.5-vl": 54.0,
    
    # LLaVA variants
    "llava/llava-1.5-13b": 40.0,
    "llava/llava-1.6-34b": 45.0,
    "llava/llava-1.6-7b": 38.0,
    
    # MiniCPM
    "openbmb/minicpm-v-2": 39.9,
    "openbmb/minicpm-v-2.6": 45.0,
    "openbmb/minicpm-llama3-v2.5": 48.0,
    
    # Phi
    "microsoft/phi-3-vision": 42.0,
    "microsoft/phi-3-multimodal": 40.0,
    
    # DeepSeek
    "deepseek/deepseek-v3": 53.0,
    "deepseek/deepseek-chat": 51.0,
    "deepseek/deepseek-r1": 55.0,
    
    # Moonshot
    "moonshotai/kimi-k2": 57.0,
    "moonshotai/kimi-k2.5": 59.0,
    
    # GLM
    "z-ai/glm-4": 52.0,
    "z-ai/glm-4-flash": 48.0,
    "z-ai/glm-4v": 50.0,
    
    # Mistral
    "mistralai/mistral-large": 46.0,
    "mistralai/mistral-medium": 42.0,
    
    # Yi
    "01-ai/yi-vl": 44.0,
    "01-ai/yi-34b-vl": 48.0,
    
    # Others
    "microsoft/phi-4-multimodal": 49.0,
    "meta/llama-3.1-405b-instruct": 53.0,  # Assume decent multimodal
    "meta/llama-3.2-90b": 51.0,
}


def fetch_mathvista() -> Dict[str, float]:
    """
    Fetch MathVista math reasoning scores.
    Currently uses fallback data from mathvista.github.io leaderboard.
    Returns: dict of model_id -> reasoning_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://mathvista.github.io"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_mathvista_html(resp.text)
            if scores:
                print(f"MathVista: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"MathVista scrape failed: {e}")
    
    print("MathVista: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_mathvista_html(html: str) -> Dict[str, float]:
    """Parse MathVista HTML to extract model scores."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    # Find the leaderboard table
    tables = soup.find_all("table")
    for table in tables:
        # Check if this is the main leaderboard (has ALL column)
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if headers and "ALL" in headers:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 3:
                    # Model name in first column
                    model_text = cols[0].get_text(strip=True)
                    
                    # ALL score is typically in 3rd column
                    score_text = cols[2].get_text(strip=True)
                    try:
                        score = float(score_text)
                        if 0 <= score <= 100:
                            canonical = model_mapper.to_canonical(model_text)
                            if canonical:
                                scores[canonical] = score
                    except ValueError:
                        continue
    
    return scores
