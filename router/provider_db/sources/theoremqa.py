"""
TheoremQA - Reasoning benchmark for STEM.
Tests ability to solve theorem-based questions.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_theoremqa() -> Dict[str, float]:
    """
    Fetch TheoremQA scores from known results.
    Returns dict: model_id -> reasoning_score (0-100).
    
    TheoremQA is a benchmark of 250 high-difficulty theorem-based
    questions requiring domain expertise to solve.
    """
    scores = _fallback_scores()
    if scores:
        print(f"TheoremQA: {len(scores)} reasoning scores (fallback)")
        return scores
    
    print("TheoremQA: no scores available")
    return {}


def _fallback_scores() -> Dict[str, float]:
    """
    Static TheoremQA scores from published results.
    """
    known = {
        # Top models (2024-2025)
        "gpt-4o": 58.0,
        "gpt-4o-mini": 42.0,
        "claude-3.5-sonnet": 62.0,
        "claude-3.5-sonnet-20241022": 62.0,
        "claude-3.5-haiku": 35.0,
        "gpt-4-turbo": 45.0,
        "gpt-4": 38.0,
        "deepseek-coder-v2": 40.0,
        "deepseek-r1": 68.0,
        "deepseek-v3": 52.0,
        "qwen-2.5-coder-32b-instruct": 42.0,
        "qwen-2.5-max": 55.0,
        "llama-3.1-405b-instruct": 45.0,
        "llama-3.1-70b-instruct": 38.0,
        "llama-3.1-8b-instruct": 22.0,
        "mistral-large": 38.0,
        "mistral-large-3": 45.0,
        "mixtral-8x22b": 35.0,
        "phi-4": 42.0,
        "phi-3-medium": 25.0,
        "gemini-1.5-pro": 48.0,
        "gemini-1.5-flash": 35.0,
        "gemini-2.0-flash": 42.0,
        "claude-3-opus": 45.0,
        "claude-3-sonnet": 35.0,
        "claude-3-haiku": 20.0,
        "grok-2": 45.0,
        "grok-2-mini": 38.0,
    }
    
    result = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            result[canonical] = score
    
    return result
