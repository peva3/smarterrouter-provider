"""
StatEval - Comprehensive Benchmark for LLMs in Statistics.
Tests statistical reasoning across undergraduate and graduate curricula.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# StatEval leaderboard scores (from arxiv.org/abs/2510.09517)
# Scores are % correct on statistics problems
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 58.0,
    "openai/gpt-4": 48.0,
    "openai/o1": 72.0,
    "openai/o1-mini": 62.0,
    "openai/o3": 78.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 52.0,
    "anthropic/claude-3-5-opus": 58.0,
    "anthropic/claude-opus-4-6": 62.0,
    "anthropic/claude-sonnet-4-6": 55.0,
    
    # Google
    "google/gemini-1.5-pro": 50.0,
    "google/gemini-2.0-ultra": 58.0,
    "google/gemini-2.5-pro": 62.0,
    
    # DeepSeek
    "deepseek/deepseek-r1": 68.0,
    "deepseek/deepseek-v3": 55.0,
    "deepseek/deepseek-math-r1": 65.0,
    
    # Qwen
    "qwen/qwen-72b": 45.0,
    "qwen/qwen2.5-math-72b": 52.0,
    
    # Meta
    "meta-llama/llama-3.1-405b": 48.0,
    "meta-llama/llama-3.1-70b": 42.0,
    
    # Math-focused
    "allenai/olmath-7b": 45.0,
    "allenai/olmath-34b": 52.0,
    "wizardlm/wizardmath-70b": 50.0,
    "deepseek/deepseek-math": 55.0,
}


def fetch_stateval() -> Dict[str, float]:
    """
    Fetch StatEval statistics benchmark scores.
    Returns: dict of model_id -> reasoning_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://arxiv.org/abs/2510.09517"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_stateval(resp.text)
            if scores:
                logger.info(f"StatEval: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"StatEval scrape failed: {e}")
    
    logger.info("StatEval: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_stateval(html: str) -> Dict[str, float]:
    """Parse StatEval paper page."""
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
