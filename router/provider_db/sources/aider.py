"""
Aider LLM Leaderboard - fetch coding scores from aider.chat.
Measures code editing ability on 225 Exercism exercises (polyglot benchmark).
"""

import re
import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# Aider polyglot leaderboard top scores (from aider.chat/docs/leaderboards)
# These are % correct on 225 coding exercises across 6 languages
FALLBACK_SCORES = {
    # Top tier (>80%)
    "openai/gpt-5-high": 88.0,
    "openai/gpt-5-medium": 86.7,
    "openai/o3-pro": 84.9,
    "google/gemini-2.5-pro-preview": 83.1,
    "openai/gpt-5-low": 81.3,
    
    # 70-80% tier
    "openai/o3": 76.9,
    "google/gemini-2.5-pro-preview-05-06": 76.9,
    "xai/grok-4": 79.6,
    "openai/gpt-4o": 75.0,
    "deepseek/deepseek-v3.2-reasoner": 74.2,
    "anthropic/claude-opus-4-20250514": 72.0,
    "openai/o4-mini": 72.0,
    "deepseek/deepseek-r1": 71.4,
    
    # 60-70% tier
    "anthropic/claude-sonnet-4-20250514": 61.3,
    "openai/o3-mini": 60.4,
    "qwen/qwen3-235b-a22b": 59.6,
    "moonshotai/kimi-k2": 59.1,
    "deepseek/deepseek-r1-0528": 56.9,
    "google/gemini-2.5-flash-preview": 55.1,
    "deepseek/deepseek-chat": 70.2,
    "openai/gpt-4.1": 52.4,
    "anthropic/claude-3-5-sonnet": 51.6,
    "xai/grok-3-beta": 53.3,
    
    # 40-60% tier
    "meta/llama-3-70b-instruct": 42.0,
    "mistralai/mistral-large-3": 45.0,
    "cohere/command-r-plus": 48.0,
    "z-ai/glm-4.7": 50.0,
    "anthropic/claude-3-haiku": 44.0,
    "google/gemma-2-27b": 40.0,
    "microsoft/phi-3-medium": 38.0,
    "meta/llama-3-8b-instruct": 35.0,
    
    # <40%
    "google/gemma-7b": 30.0,
    "microsoft/phi-3-mini": 28.0,
}


def fetch_aider() -> Dict[str, float]:
    """
    Fetch Aider coding leaderboard scores.
    Currently uses fallback data from aider.chat leaderboard.
    Returns: dict of model_id -> coding_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://aider.chat/docs/leaderboards/"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_aider_html(resp.text)
            if scores:
                print(f"Aider: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"Aider scrape failed: {e}")
    
    print("Aider: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_aider_html(html: str) -> Dict[str, float]:
    """Parse Aider leaderboard HTML to extract model scores."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    # Find the main leaderboard table
    tables = soup.find_all("table")
    for table in tables:
        # Check if this is the polyglot leaderboard
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if headers and "Percent correct" in headers:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    # Model name is in first column (may have nested elements)
                    model_cell = cols[0]
                    model_text = model_cell.get_text(strip=True)
                    
                    # Percent correct is in second column
                    percent_text = cols[1].get_text(strip=True)
                    
                    # Extract numeric percentage
                    match = re.search(r"([\d.]+)%", percent_text)
                    if match:
                        try:
                            score = float(match.group(1))
                            if 0 <= score <= 100:
                                canonical = model_mapper.to_canonical(model_text)
                                if canonical:
                                    scores[canonical] = score
                        except ValueError:
                            continue
    
    return scores
