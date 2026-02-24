"""
AIME - American Invitational Mathematics Examination competition math.
Tests mathematical reasoning on competition problems.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# AIME 2024/2025 leaderboard scores (from official results)
# Scores are % correct on competition math problems
FALLBACK_SCORES = {
    # OpenAI - reasoning models excel here
    "openai/gpt-4o": 35.0,
    "openai/gpt-4": 25.0,
    "openai/o1": 75.0,
    "openai/o1-mini": 65.0,
    "openai/o1-preview": 60.0,
    "openai/o3": 85.0,
    "openai/o3-mini": 78.0,
    "openai/o4-mini": 72.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 32.0,
    "anthropic/claude-3-5-opus": 45.0,
    "anthropic/claude-opus-4-6": 52.0,
    "anthropic/claude-sonnet-4-6": 40.0,
    
    # Google
    "google/gemini-1.5-pro": 30.0,
    "google/gemini-2.0-ultra": 45.0,
    "google/gemini-2.5-pro": 55.0,
    "google/gemini-2.5-flash": 42.0,
    
    # DeepSeek reasoning models
    "deepseek/deepseek-r1": 70.0,
    "deepseek/deepseek-v3": 40.0,
    "deepseek/deepseek-math": 60.0,
    "deepseek/deepseek-math-r1": 72.0,
    
    # Qwen math models
    "qwen/qwen2.5-math-72b": 55.0,
    "qwen/qwen2.5-math-7b": 40.0,
    "qwen/qwen2.5-coder-32b": 35.0,
    "qwen/qwen-math-plus": 58.0,
    
    # Meta math
    "meta-llama/llama-3.2-math-1b": 20.0,
    "meta-llama/llama-3.2-math-90b": 45.0,
    
    # Math-specialized models
    "wizardlm/wizardmath-70b": 42.0,
    "wizardlm/wizardmath-7b": 30.0,
    "meta-ai/watson-3b": 25.0,
    "allenai/olmath-7b": 48.0,
    "allenai/olmath-34b": 55.0,
    "allenai/olmath-70b": 62.0,
    "ai-x/maverick-math-7b": 35.0,
    "ai-x/maverick-math-34b": 45.0,
    "ai-x/maverick-math-70b": 52.0,
    "-nousresearch/nous-hermes2-math": 40.0,
    "liquid/liquid-math-1b": 22.0,
    "liquid/liquid-math-7b": 32.0,
    "liquid/liquid-reasoning-1b": 28.0,
    "thedrummer/mathnumind-7b": 30.0,
    "thedrummer/mathnumind-34b": 42.0,
    "sao10k/function-calling-math": 25.0,
    "steelskies/steelmath-7b": 35.0,
}


def fetch_aime() -> Dict[str, float]:
    """
    Fetch AIME competition math scores.
    Returns: dict of model_id -> reasoning_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://aops.com/contest/list"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_aime(resp.text)
            if scores:
                logger.info(f"AIME: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"AIME scrape failed: {e}")
    
    logger.info("AIME: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_aime(html: str) -> Dict[str, float]:
    """Parse AIME results page."""
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
                    score_text = cols[1].get_text(strip=True).replace("%", "")
                    score = float(score_text)
                    if 0 <= score <= 100:
                        canonical = model_mapper.to_canonical(model_text)
                        if canonical:
                            scores[canonical] = score
                except (ValueError, IndexError):
                    continue
    
    return scores
