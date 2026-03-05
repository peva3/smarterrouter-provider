"""
CruxEval - Code reasoning benchmark.
Tests ability to predict code output and execution.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_cruxeval() -> Dict[str, float]:
    """
    Fetch CruxEval scores from known results.
    Returns dict: model_id -> reasoning_score (0-100).
    
    CruxEval tests code understanding through output prediction
    and execution reasoning tasks.
    """
    scores = _fallback_scores()
    if scores:
        print(f"CruxEval: {len(scores)} reasoning scores (fallback)")
        return scores
    
    print("CruxEval: no scores available")
    return {}


def _fallback_scores() -> Dict[str, float]:
    """
    Static CruxEval scores from published results.
    """
    known = {
        # Top models (2024-2025)
        "gpt-4o": 72.0,
        "gpt-4o-mini": 65.0,
        "claude-3.5-sonnet": 75.0,
        "claude-3.5-sonnet-20241022": 75.0,
        "claude-3.5-haiku": 58.0,
        "gpt-4-turbo": 65.0,
        "gpt-4": 58.0,
        "deepseek-coder-v2": 68.0,
        "deepseek-coder-v2.5": 70.0,
        "deepseek-coder": 55.0,
        "deepseek-r1": 78.0,
        "deepseek-v3": 72.0,
        "qwen-2.5-coder-32b-instruct": 62.0,
        "qwen-2.5-coder": 55.0,
        "qwen-2.5vl-32b-instruct": 58.0,
        "llama-3.1-405b-instruct": 60.0,
        "llama-3.1-70b-instruct": 52.0,
        "llama-3.1-8b-instruct": 38.0,
        "llama-3-70b-instruct": 48.0,
        "llama-3-8b-instruct": 32.0,
        "mistral-large": 52.0,
        "mistral-large-3": 58.0,
        "mixtral-8x22b": 48.0,
        "mixtral-8x7b": 40.0,
        "starcoder-2-15b": 42.0,
        "phi-4": 52.0,
        "phi-3-medium": 38.0,
        "gemini-1.5-pro": 58.0,
        "gemini-1.5-flash": 50.0,
        "gemini-2.0-flash": 55.0,
        "claude-3-opus": 55.0,
        "claude-3-sonnet": 45.0,
        "claude-3-haiku": 32.0,
        "grok-2": 55.0,
        "grok-2-mini": 48.0,
    }
    
    result = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            result[canonical] = score
    
    return result
