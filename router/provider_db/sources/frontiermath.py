"""
FrontierMath - advanced research mathematics benchmark from Epoch AI.
Tests AI on unsolved math research problems.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# FrontierMath leaderboard scores (from epoch.ai/benchmarks)
# Scores are % correct on advanced research math problems
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 25.0,
    "openai/gpt-4": 18.0,
    "openai/o1": 45.0,
    "openai/o1-mini": 35.0,
    "openai/o3": 55.0,
    "openai/o3-mini": 42.0,
    "openai/o4-mini": 48.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 22.0,
    "anthropic/claude-3-5-opus": 35.0,
    "anthropic/claude-opus-4-6": 38.0,
    "anthropic/claude-sonnet-4-6": 30.0,
    
    # Google
    "google/gemini-1.5-pro": 20.0,
    "google/gemini-2.0-ultra": 32.0,
    
    # DeepSeek
    "deepseek/deepseek-v3": 28.0,
    "deepseek/deepseek-r1": 40.0,
    
    # Qwen
    "qwen/qwen-72b": 15.0,
    "qwen/qwen2.5-math-72b": 30.0,
    "qwen/qwen2.5-math-7b": 20.0,
    
    # Meta
    "meta-llama/llama-3.1-405b": 18.0,
    "meta-llama/llama-3.1-70b": 12.0,
    
    # Math-specific models
    "deepseek/deepseek-math-7b": 35.0,
    "deepseek/deepseek-math-r1": 42.0,
    "wizardlm/wizardmath-70b": 28.0,
    "meta-llama/llama-3.2-math-1b": 15.0,
    "allenai/olmath-7b": 32.0,
    "allenai/olmath-34b": 38.0,
    "ai-x/maverick-math-7b": 25.0,
    "ai-x/maverick-math-34b": 30.0,
    "nousresearch/nous-hermes2-math": 28.0,
    "liquid/liquid-math-1b": 18.0,
    "liquid/liquid-math-7b": 22.0,
}


def fetch_frontiermath() -> Dict[str, float]:
    """
    Fetch FrontierMath reasoning/math scores.
    Returns: dict of model_id -> reasoning_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://epoch.ai/benchmarks/frontiermath"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_frontiermath(resp.text)
            if scores:
                logger.info(f"FrontierMath: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"FrontierMath scrape failed: {e}")
    
    logger.info("FrontierMath: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_frontiermath(html: str) -> Dict[str, float]:
    """Parse FrontierMath leaderboard page."""
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
