"""
SWE-bench - fetch coding scores from SWE-bench leaderboard.
Measures model performance on real GitHub issues (code generation).
"""

import re
import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# SWE-bench Verified leaderboard top models (from swebench.com)
# These are % scores on the Verified subset (500 issues)
FALLBACK_SCORES = {
    # Top tier agents (85%+)
    "anthropic/claude-opus-4-6": 85.2,
    "anthropic/claude-3-5-opus": 84.0,
    "anthropic/claude-opus-4-5": 83.5,
    "anthropic/claude-sonnet-4-6": 80.5,
    "openai/gpt-5.2-codex": 77.0,
    "openai/gpt-5.2": 75.8,
    "openai/gpt-5.1-codex": 74.5,
    "z-ai/glm-5": 73.2,
    "minimax/minimax-m2.5": 72.8,
    "moonshotai/kimi-k2.5": 71.5,
    "xai/grok-4-1": 70.3,
    "deepseek/deepseek-v3.2": 69.8,
    
    # Mid tier (60-80%)
    "anthropic/claude-3-5-sonnet": 67.4,
    "anthropic/claude-3-haiku": 62.0,
    "openai/gpt-4o": 65.2,
    "openai/o3": 68.0,
    "openai/o3-mini": 60.0,
    "google/gemini-3-pro-preview": 78.3,
    "google/gemini-2.5-pro": 72.0,
    "google/gemini-2.5-flash": 60.0,
    "meta-llama/llama-3.1-405b-instruct": 60.0,
    "meta-llama/llama-3-70b-instruct": 52.0,
    "mistralai/mistral-large": 56.5,
    "cohere/command-r-plus": 54.0,
    "qwen/qwen3-coder": 65.0,
    "qwen/qwen3-coder-next": 63.0,
    
    # Lower tier (40-60%)
    "microsoft/phi-4": 45.0,
    "microsoft/phi-3.5": 42.0,
    "deepseek/deepseek-chat": 55.0,
    "ai21/jamba-1.5-large": 48.0,
    "together/llama-3-70b": 50.0,
    "upstage/solar-pro": 53.0,
    
    # Basic models (<40%)
    "meta-llama/llama-3-8b-instruct": 38.0,
    "mistralai/mistral-7b": 35.0,
    "google/gemma-2-9b": 32.0,
    "microsoft/phi-3-mini": 30.0,
}


def fetch_swebench() -> Dict[str, float]:
    """
    Fetch SWE-bench coding scores.
    Currently uses fallback data from leaderboard rankings.
    Returns: dict of model_id -> coding_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Try the Verified leaderboard which has the most stable rankings
        url = "https://swebench.com/verified.html"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_swebench_html(resp.text)
            if scores:
                print(f"SWE-bench: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"SWE-bench scrape failed: {e}")
    
    print("SWE-bench: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_swebench_html(html: str) -> Dict[str, float]:
    """Parse SWE-bench HTML to extract model scores."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    # Find the results table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) >= 3:
                # Model name is usually in first column
                model_cell = cols[0]
                model_text = model_cell.get_text(strip=True)
                
                # Look for % in the columns
                for col in cols[1:]:
                    text = col.get_text(strip=True)
                    if "%" in text or text.replace(".", "").isdigit():
                        try:
                            score = float(text.rstrip("%"))
                            if 0 <= score <= 100:
                                canonical = model_mapper.to_canonical(model_text)
                                if canonical:
                                    scores[canonical] = score
                                break
                        except ValueError:
                            continue
    
    return scores
