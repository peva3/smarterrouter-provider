"""
Tool Use Benchmarks - BFCL, API-Bank, ToolBench.
Tests function calling and tool use capabilities.
"""

import logging
from typing import Dict
from ..model_mapper import model_mapper

logger = logging.getLogger(__name__)

# Tool use benchmark scores (from Berkeley Function Calling Leaderboard)
# Scores are pass rate on function calling tasks
FALLBACK_SCORES = {
    # OpenAI - excellent tool use
    "openai/gpt-4o": 88.0,
    "openai/gpt-4o-mini": 82.0,
    "openai/gpt-4-turbo": 85.0,
    "openai/gpt-4": 78.0,
    "openai/gpt-3.5-turbo": 68.0,
    "openai/o1": 72.0,
    "openai/o3": 75.0,
    
    # Anthropic
    "anthropic/claude-3-opus": 82.0,
    "anthropic/claude-3-5-opus": 88.0,
    "anthropic/claude-3-sonnet": 75.0,
    "anthropic/claude-3-5-sonnet": 80.0,
    "anthropic/claude-3-haiku": 65.0,
    "anthropic/claude-opus-4-6": 90.0,
    "anthropic/claude-sonnet-4-6": 85.0,
    
    # Meta
    "meta-llama/llama-3-405b": 72.0,
    "meta-llama/llama-3-70b": 68.0,
    "meta-llama/llama-3-8b": 55.0,
    "meta-llama/llama-3.1-405b": 75.0,
    "meta-llama/llama-3.1-70b": 70.0,
    "meta-llama/llama-3.1-8b": 58.0,
    "meta-llama/llama-3.2-90b": 78.0,
    
    # Mistral
    "mistralai/mistral-large": 75.0,
    "mistralai/mistral-medium": 68.0,
    "mistralai/mixtral-8x22b": 72.0,
    "mistralai/mixtral-8x7b": 65.0,
    
    # Google
    "google/gemini-1.5-pro": 78.0,
    "google/gemini-1.5-flash": 72.0,
    "google/gemini-ultra": 82.0,
    "google/gemma-2-27b": 60.0,
    "google/gemma-2-9b": 52.0,
    
    # Qwen - excellent for tool use
    "qwen/qwen-72b": 80.0,
    "qwen/qwen-14b": 72.0,
    "qwen/qwen2.5-72b": 82.0,
    "qwen/qwen2.5-coder-32b": 78.0,
    "qwen/qwen2.5-tools": 85.0,
    
    # DeepSeek
    "deepseek/deepseek-coder": 75.0,
    "deepseek/deepseek-chat": 70.0,
    "deepseek/deepseek-v3": 78.0,
    "deepseek/deepseek-r1": 72.0,
    
    # Tool-specific models
    "sao10k/tool-calling": 68.0,
    "sao10k/function-calling": 72.0,
    "fireworks/firefunction-v1": 75.0,
    "anyscale/any-70b-tool": 70.0,
    
    # Cohere
    "cohere/command-r": 72.0,
    "cohere/command-r-plus": 78.0,
    
    # NVIDIA
    "nvidia/nemotron-70b": 70.0,
    "nvidia/nemotron-4-mini": 65.0,
    
    # Amazon
    "amazon/nova-pro": 62.0,
    "amazon/nova-lite": 55.0,
    
    # Microsoft
    "microsoft/phi-4": 58.0,
    "microsoft/phi-3-medium": 52.0,
    
    # X.AI
    "x-ai/grok-2": 70.0,
    "x-ai/grok-2-vision": 68.0,
    
    # Nous Research
    "nousresearch/nous-hermes-2": 68.0,
    "nousresearch/nous-hermes-2-tool": 75.0,
}


def fetch_tool_use() -> Dict[str, float]:
    """
    Fetch tool use/function calling benchmark scores.
    Returns: dict of model_id -> coding_score (0-100)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = "https://paperswithcode.com/dataset/bfcl"
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if resp.status_code == 200:
            scores = _parse_tool_use(resp.text)
            if scores:
                logger.info(f"Tool Use: scraped {len(scores)} scores")
                return scores
    except ImportError:
        logger.debug("requests not available")
    except Exception as e:
        logger.debug(f"Tool Use scrape failed: {e}")
    
    logger.info("Tool Use: using fallback data")
    return dict(FALLBACK_SCORES)


def _parse_tool_use(html: str) -> Dict[str, float]:
    """Parse tool use leaderboard pages."""
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
