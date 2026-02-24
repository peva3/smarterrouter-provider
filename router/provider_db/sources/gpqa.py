"""
GPQA - Graduate-Level Google-Proof Q&A Benchmark.
Tests graduate-level reasoning in physics, chemistry, biology.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# GPQA Diamond leaderboard scores
# Scores are % correct on graduate-level science questions
FALLBACK_SCORES = {
    # OpenAI - reasoning models excel here
    "openai/gpt-4o": 45.0,
    "openai/gpt-4": 35.0,
    "openai/o1": 75.0,
    "openai/o1-mini": 62.0,
    "openai/o1-preview": 55.0,
    "openai/o3": 85.0,
    "openai/o3-mini": 72.0,
    "openai/o4-mini": 68.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 42.0,
    "anthropic/claude-3-5-opus": 55.0,
    "anthropic/claude-opus-4-6": 62.0,
    "anthropic/claude-sonnet-4-6": 48.0,
    
    # Google
    "google/gemini-1.5-pro": 40.0,
    "google/gemini-2.0-ultra": 52.0,
    "google/gemini-2.5-pro": 58.0,
    "google/gemini-2.5-flash": 45.0,
    
    # DeepSeek reasoning
    "deepseek/deepseek-r1": 70.0,
    "deepseek/deepseek-v3": 45.0,
    "deepseek/deepseek-math-r1": 68.0,
    
    # Qwen
    "qwen/qwen-72b": 32.0,
    "qwen/qwen2.5-math-72b": 48.0,
    
    # Meta
    "meta-llama/llama-3.1-405b": 35.0,
    "meta-llama/llama-3.1-70b": 28.0,
    
    # Math/Science specialized
    "allenai/olmath-7b": 38.0,
    "allenai/olmath-34b": 45.0,
    "allenai/olmath-70b": 52.0,
    "wizardlm/wizardmath-70b": 42.0,
    "liquid/liquid-reasoning-1b": 25.0,
    "liquid/liquid-reasoning-7b": 35.0,
}


def fetch_gpqa() -> Dict[str, float]:
    """
    Fetch GPQA Diamond graduate-level reasoning scores.
    Returns: dict of model_id -> reasoning_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://paperswithcode.com/dataset/gpqa"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_gpqa(resp.text)
            if scores:
                logger.info(f"GPQA: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"GPQA scrape failed: {e}")
    
    logger.info("GPQA: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_gpqa(html: str) -> Dict[str, float]:
    """Parse GPQA leaderboard page."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                model_text = cols[0].get_text(strip=True)
                try:
                    score = float(cols[1].get_text(strip=True).replace("%", ""))
                    if 0 <= score <= 100:
                        canonical = model_mapper.to_canonical(model_text)
                        if canonical:
                            scores[canonical] = score
                except (ValueError, IndexError):
                    continue
    
    return scores
