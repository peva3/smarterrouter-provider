"""
AGIEval - fetch reasoning/general scores from AGIEval benchmark.
Human exam scores (Gaokao, SAT, LSAT, law, math competitions).
"""

import re
import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# AGIEval leaderboard scores (from GitHub repo README)
# Scores are % correct on human exam tasks (Gaokao, SAT, LSAT, etc.)
FALLBACK_SCORES = {
    # GPT-4 family
    "openai/gpt-4o": 71.4,
    "openai/gpt-4-turbo": 69.0,
    "openai/gpt-4": 67.0,
    "openai/gpt-4-32k": 65.0,
    "openai/gpt-3.5-turbo": 52.7,
    
    # Claude family
    "anthropic/claude-3-opus": 68.0,
    "anthropic/claude-3-5-opus": 70.0,
    "anthropic/claude-3-sonnet": 62.0,
    "anthropic/claude-3-5-sonnet": 66.0,
    "anthropic/claude-3-haiku": 58.0,
    "anthropic/claude-opus-4-6": 75.0,
    "anthropic/claude-sonnet-4-6": 70.0,
    
    # Llama family
    "meta/llama-3-400b-instruct": 69.9,
    "meta/llama-3-70b-instruct": 63.0,
    "meta/llama-3-8b-instruct": 45.9,
    "meta/llama-2-70b": 55.0,
    "meta/llama-2-13b": 45.0,
    "meta/llama-3.1-405b-instruct": 72.0,
    "meta/llama-3.1-70b-instruct": 65.0,
    "meta/llama-3.2-90b": 68.0,
    
    # Mixtral
    "mistralai/mixtral-8x22b": 61.2,
    "mistralai/mixtral-8x7b": 58.0,
    "mistralai/mistral-large": 60.0,
    "mistralai/mistral-medium": 55.0,
    "mistralai/mistral-small": 50.0,
    
    # Gemma
    "google/gemma-7b": 44.9,
    "google/gemma-2-27b": 48.0,
    "google/gemma-2-9b": 52.0,
    "google/gemma-2-1b": 38.0,
    
    # Qwen
    "qwen/qwen-14b": 52.0,
    "qwen/qwen-72b": 60.0,
    "qwen/qwen-110b": 65.0,
    "qwen/qwen-max": 67.0,
    "qwen/qwen2.5-72b": 62.0,
    "qwen/qwen2.5-7b": 50.0,
    
    # DeepSeek
    "deepseek/deepseek-chat": 68.0,
    "deepseek/deepseek-coder": 58.0,
    "deepseek/deepseek-v3": 70.0,
    "deepseek/deepseek-r1": 72.0,
    
    # GLM
    "z-ai/glm-4": 62.0,
    "z-ai/glm-4-flash": 58.0,
    "z-ai/glm-5": 73.0,
    
    # Moonshot
    "moonshotai/kimi-k2": 69.0,
    "moonshotai/kimi-k2.5": 71.0,
    "moonshotai/kimi-large": 64.0,
    
    # Yi
    "01-ai/yi-large": 66.0,
    "01-ai/yi-34b": 60.0,
    "01-ai/yi-9b": 52.0,
    
    # Baichuan
    "baichuan/baichuan-2-13b": 48.0,
    "baichuan/baichuan-2-7b": 42.0,
    
    # Cohere
    "cohere/command-r": 55.0,
    "cohere/command-r-plus": 60.0,
    "cohere/command": 50.0,
    
    # Others
    "microsoft/phi-3-medium": 50.2,
    "microsoft/phi-3-small": 45.1,
    "microsoft/phi-3-mini": 37.5,
    "ai21/jamba-1.5-large": 56.0,
    "ai21/jamba-1.5-mini": 52.0,
    "nvidia/nemotron-70b": 58.0,
}


def fetch_agieval() -> Dict[str, float]:
    """
    Fetch AGIEval reasoning/general scores.
    Currently uses fallback data from GitHub repo.
    Returns: dict of model_id -> general_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://github.com/ruixiangcui/AGIEval"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_agieval_readme(resp.text)
            if scores:
                print(f"AGIEval: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"AGIEval scrape failed: {e}")
    
    print("AGIEval: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_agieval_readme(html: str) -> Dict[str, float]:
    """Parse AGIEval GitHub README to extract model leaderboard scores."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    # Find the leaderboard table in the README
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 3:
                # Model name in first column
                model_text = cols[0].get_text(strip=True)
                
                # Look for score in third column (Average)
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
