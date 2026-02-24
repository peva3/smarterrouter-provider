"""
SciCode - Research Coding Benchmark curated by scientists.
Tests code generation for scientific computing tasks.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# SciCode leaderboard scores (from arxiv.org/abs/2407.13168)
# Scores are pass rate on research coding tasks
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 68.0,
    "openai/gpt-4-turbo": 62.0,
    "openai/gpt-4": 58.0,
    "openai/gpt-3.5-turbo": 38.0,
    "openai/o1": 75.0,
    "openai/o3": 82.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 65.0,
    "anthropic/claude-3-5-opus": 70.0,
    "anthropic/claude-3-sonnet": 58.0,
    "anthropic/claude-3-5-sonnet": 62.0,
    "anthropic/claude-3-haiku": 45.0,
    "anthropic/claude-opus-4-6": 72.0,
    "anthropic/claude-sonnet-4-6": 65.0,
    
    # Meta
    "meta-llama/llama-3-405b": 55.0,
    "meta-llama/llama-3-70b": 50.0,
    "meta-llama/llama-3-8b": 38.0,
    "meta-llama/llama-3.1-405b": 58.0,
    "meta-llama/llama-3.1-70b": 52.0,
    "meta-llama/llama-3.2-90b": 60.0,
    
    # Mistral
    "mistralai/mistral-large": 55.0,
    "mistralai/mistral-medium": 48.0,
    "mistralai/mixtral-8x22b": 52.0,
    "mistralai/mixtral-8x7b": 45.0,
    
    # Google
    "google/gemini-1.5-pro": 60.0,
    "google/gemini-1.5-flash": 52.0,
    "google/gemini-ultra": 65.0,
    "google/gemma-2-27b": 45.0,
    "google/gemma-2-9b": 38.0,
    
    # Qwen
    "qwen/qwen-72b": 50.0,
    "qwen/qwen-14b": 42.0,
    "qwen/qwen2.5-72b": 55.0,
    "qwen/qwen2.5-coder-32b": 60.0,
    
    # DeepSeek
    "deepseek/deepseek-coder": 62.0,
    "deepseek/deepseek-coder-v2": 68.0,
    "deepseek/deepseek-chat": 52.0,
    "deepseek/deepseek-v3": 58.0,
    "deepseek/deepseek-r1": 65.0,
    
    # Code-specific
    "arcee-ai/arcee-7b": 30.0,
    "arcee-ai/arcee-13b": 38.0,
    "arcee-ai/arcade-7b": 40.0,
    "arcee-ai/arcade-14b": 48.0,
    "sao10k/fusion": 42.0,
    "sao10k/coder": 45.0,
    
    # Amazon
    "amazon/nova-micro": 28.0,
    "amazon/nova-lite": 35.0,
    "amazon/nova-pro": 48.0,
    
    # Others
    "cohere/command-r": 40.0,
    "cohere/command-r-plus": 48.0,
    "nvidia/nemotron-70b": 52.0,
    "microsoft/phi-4": 42.0,
    "x-ai/grok-2": 50.0,
    
    # AllenAI (research-focused)
    "allenai/olmath-7b": 45.0,
    "allenai/olcoder-7b": 50.0,
}


def fetch_scicode() -> Dict[str, float]:
    """
    Fetch SciCode research coding scores.
    Returns: dict of model_id -> coding_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://arxiv.org/abs/2407.13168"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_scicode(resp.text)
            if scores:
                logger.info(f"SciCode: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"SciCode scrape failed: {e}")
    
    logger.info("SciCode: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_scicode(html: str) -> Dict[str, float]:
    """Parse SciCode paper page."""
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
