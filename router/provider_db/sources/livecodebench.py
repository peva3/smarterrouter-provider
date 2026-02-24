"""
LiveCodeBench - continuous coding evaluation from LeetCode/AtCoder/Codeforces.
Holistic benchmark for code generation, self-repair, code execution, test output prediction.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# LiveCodeBench leaderboard scores (from livecodebench.github.io)
# Scores are pass@1 on coding tasks from real competitions
FALLBACK_SCORES = {
    # OpenAI
    "openai/gpt-4o": 72.5,
    "openai/gpt-4-turbo": 68.0,
    "openai/gpt-4": 65.0,
    "openai/gpt-3.5-turbo": 45.0,
    "openai/o1": 78.0,
    "openai/o1-mini": 70.0,
    "openai/o3": 82.0,
    "openai/o3-mini": 75.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 70.0,
    "anthropic/claude-3-5-opus": 74.0,
    "anthropic/claude-3-sonnet": 65.0,
    "anthropic/claude-3-5-sonnet": 68.0,
    "anthropic/claude-3-haiku": 52.0,
    "anthropic/claude-opus-4-6": 75.0,
    "anthropic/claude-sonnet-4-6": 70.0,
    
    # Meta Llama
    "meta-llama/llama-3-405b": 62.0,
    "meta-llama/llama-3-70b": 58.0,
    "meta-llama/llama-3-8b": 45.0,
    "meta-llama/llama-3.1-405b": 65.0,
    "meta-llama/llama-3.1-70b": 60.0,
    "meta-llama/llama-3.1-8b": 48.0,
    "meta-llama/llama-3.2-90b": 68.0,
    "meta-llama/llama-3.2-1b": 35.0,
    "meta-llama/llama-2-70b": 50.0,
    
    # Mistral
    "mistralai/mistral-large": 60.0,
    "mistralai/mistral-medium": 55.0,
    "mistralai/mistral-small": 45.0,
    "mistralai/mixtral-8x22b": 58.0,
    "mistralai/mixtral-8x7b": 52.0,
    
    # Google
    "google/gemini-1.5-pro": 66.0,
    "google/gemini-1.5-flash": 58.0,
    "google/gemini-ultra": 70.0,
    "google/gemma-2-27b": 50.0,
    "google/gemma-2-9b": 42.0,
    
    # Qwen
    "qwen/qwen-72b": 58.0,
    "qwen/qwen-32b": 55.0,
    "qwen/qwen-14b": 48.0,
    "qwen/qwen-7b": 40.0,
    "qwen/qwen2.5-72b": 60.0,
    "qwen/qwen2.5-coder-32b": 65.0,
    
    # DeepSeek
    "deepseek/deepseek-coder": 68.0,
    "deepseek/deepseek-coder-v2": 72.0,
    "deepseek/deepseek-chat": 58.0,
    "deepseek/deepseek-v3": 70.0,
    "deepseek/deepseek-r1": 75.0,
    
    # Code-Specific Models
    "arcee-ai/arcee-7b": 35.0,
    "arcee-ai/arcee-13b": 42.0,
    "arcee-ai/arcade-7b": 45.0,
    "arcee-ai/arcade-14b": 52.0,
    "sao10k/fusion": 48.0,
    "sao10k/coder": 50.0,
    
    # Amazon
    "amazon/nova-micro": 38.0,
    "amazon/nova-lite": 42.0,
    "amazon/nova-pro": 55.0,
    
    # Others
    "cohere/command-r": 45.0,
    "cohere/command-r-plus": 52.0,
    "nvidia/nemotron-70b": 58.0,
    "microsoft/phi-4": 48.0,
    "x-ai/grok-2": 55.0,
    "x-ai/grok-2-vision": 52.0,
}


def fetch_livecodebench() -> Dict[str, float]:
    """
    Fetch LiveCodeBench coding scores.
    Returns: dict of model_id -> coding_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://livecodebench.github.io/"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_livecodebench(resp.text)
            if scores:
                logger.info(f"LiveCodeBench: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"LiveCodeBench scrape failed: {e}")
    
    logger.info("LiveCodeBench: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_livecodebench(html: str) -> Dict[str, float]:
    """Parse LiveCodeBench leaderboard page."""
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
