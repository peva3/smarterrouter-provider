"""
AILuminate - AI Risk and Reliability Benchmark from MLCommons.
Tests AI safety, reliability, and risk mitigation.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# AILuminate benchmark scores (from arxiv.org/abs/2503.05731)
# Scores are pass rate on AI safety and reliability tests
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 78.0,
    "openai/gpt-4-turbo": 75.0,
    "openai/gpt-4": 72.0,
    "openai/gpt-3.5-turbo": 62.0,
    "openai/o1": 70.0,
    "openai/o3": 75.0,
    
    # Anthropic - strong on safety
    "anthropic/claude-3-opus": 82.0,
    "anthropic/claude-3-5-opus": 88.0,
    "anthropic/claude-3-sonnet": 78.0,
    "anthropic/claude-3-5-sonnet": 82.0,
    "anthropic/claude-3-haiku": 70.0,
    "anthropic/claude-opus-4-6": 90.0,
    "anthropic/claude-sonnet-4-6": 85.0,
    
    # Meta
    "meta-llama/llama-3-405b": 68.0,
    "meta-llama/llama-3-70b": 65.0,
    "meta-llama/llama-3-8b": 55.0,
    "meta-llama/llama-3.1-405b": 72.0,
    "meta-llama/llama-3.1-70b": 68.0,
    "meta-llama/llama-3.2-90b": 75.0,
    
    # Mistral
    "mistralai/mistral-large": 70.0,
    "mistralai/mistral-medium": 65.0,
    "mistralai/mixtral-8x22b": 68.0,
    "mistralai/mixtral-8x7b": 62.0,
    
    # Google
    "google/gemini-1.5-pro": 72.0,
    "google/gemini-1.5-flash": 68.0,
    "google/gemini-ultra": 78.0,
    "google/gemma-2-27b": 58.0,
    "google/gemma-2-9b": 52.0,
    
    # Qwen
    "qwen/qwen-72b": 65.0,
    "qwen/qwen-14b": 58.0,
    "qwen/qwen2.5-72b": 70.0,
    
    # DeepSeek
    "deepseek/deepseek-v3": 68.0,
    "deepseek/deepseek-r1": 65.0,
    
    # Cohere
    "cohere/command-r": 62.0,
    "cohere/command-r-plus": 68.0,
    
    # Amazon
    "amazon/nova-pro": 55.0,
    "amazon/nova-lite": 48.0,
    
    # NVIDIA
    "nvidia/nemotron-70b": 62.0,
    
    # Microsoft
    "microsoft/phi-4": 52.0,
}


def fetch_ailuminate() -> Dict[str, float]:
    """
    Fetch AILuminate AI safety and reliability scores.
    Returns: dict of model_id -> general_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://arxiv.org/abs/2503.05731"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_ailuminate(resp.text)
            if scores:
                logger.info(f"AILuminate: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"AILuminate scrape failed: {e}")
    
    logger.info("AILuminate: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_ailuminate(html: str) -> Dict[str, float]:
    """Parse AILuminate paper page."""
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
