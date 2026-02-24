"""
EQ-Bench - Creative writing benchmark from eqbench.com.
Measures longform creative writing quality using LLM-as-judge.
"""

import re
import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

EQBENCH_URL = "https://eqbench.com/creative_writing_longform.html"


FALLBACK_QUALITY = {
    "claude-opus-4-6": 92.5,
    "claude-opus-4-5": 91.0,
    "claude-sonnet-4-6": 88.0,
    "claude-sonnet-4-5": 86.5,
    "gpt-4o": 85.0,
    "gpt-5": 87.0,
    "gemini-2-pro": 82.0,
    "gemini-2-flash": 78.0,
    "llama-3-70b": 75.0,
    "llama-3-8b": 68.0,
}


def fetch_eqbench() -> Dict[str, float]:
    """
    Fetch creative writing scores from eqbench.com.
    Returns: dict of model_id -> quality_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        resp = requests.get(EQBENCH_URL, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_eqbench_html(resp.text)
            if scores:
                print(f"EQ-Bench: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests or beautifulsoup4 not available")
    except Exception as e:
        logger.debug(f"EQ-Bench scrape failed: {e}")
    
    print("EQ-Bench: using fallback data")
    return dict(FALLBACK_QUALITY)


def _parse_eqbench_html(html: str) -> Dict[str, float]:
    """Parse eqbench HTML to extract model scores."""
    from bs4 import BeautifulSoup
    
    scores = {}
    soup = BeautifulSoup(html, "lxml")
    
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                model_link = cols[0].find("a")
                model_name = model_link.get_text(strip=True) if model_link else cols[0].get_text(strip=True)
                
                score_text = cols[-1].get_text(strip=True)
                try:
                    score = float(re.sub(r"[^\d.]", "", score_text))
                    if 0 <= score <= 100:
                        canonical = model_mapper.to_canonical(model_name)
                        if canonical:
                            scores[canonical] = score
                except (ValueError, TypeError):
                    continue
    
    return scores
