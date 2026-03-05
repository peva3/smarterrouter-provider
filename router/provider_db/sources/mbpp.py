"""
MBPP (Mostly Basic Programming Problems) - Code generation benchmark.
Tests Python code generation from natural language descriptions.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_mbpp() -> Dict[str, float]:
    """
    Fetch MBPP (Magicoder) scores from known results.
    Returns dict: model_id -> coding_score (0-100).
    
    MBPP contains 974 Python programming problems designed for
    evaluating code generation abilities. Magicoder variant uses
    enhanced prompts.
    """
    scores = _fallback_scores()
    if scores:
        print(f"MBPP: {len(scores)} coding scores (fallback)")
        return scores
    
    print("MBPP: no scores available")
    return {}


def _fallback_scores() -> Dict[str, float]:
    """
    Static MBPP scores from published results.
    These are pass rates (percentage of problems solved).
    """
    known = {
        # Top coding models (2024-2025)
        "gpt-4o": 85.0,
        "gpt-4o-mini": 82.0,
        "claude-3.5-sonnet": 88.0,
        "claude-3.5-sonnet-20241022": 88.0,
        "claude-3.5-haiku": 75.0,
        "gpt-4-turbo": 80.0,
        "gpt-4": 75.0,
        "deepseek-coder-v2": 82.0,
        "deepseek-coder-v2.5": 85.0,
        "deepseek-coder": 72.0,
        "deepseek-r1": 70.0,
        "qwen-2.5-coder-32b-instruct": 78.0,
        "qwen-2.5-coder": 74.0,
        "codeqwen-1.5-7b": 70.0,
        "llama-3.1-405b-instruct": 76.0,
        "llama-3.1-70b-instruct": 68.0,
        "llama-3.1-8b-instruct": 52.0,
        "llama-3-70b-instruct": 65.0,
        "llama-3-8b-instruct": 48.0,
        "mistral-large": 68.0,
        "mistral-large-3": 72.0,
        "mixtral-8x22b": 65.0,
        "mixtral-8x7b": 58.0,
        "starcoder-2-15b": 62.0,
        "starcoder-2": 58.0,
        "starcoder": 52.0,
        "phi-4": 68.0,
        "phi-3-medium": 55.0,
        "phi-3-mini": 45.0,
        "gemini-1.5-pro": 72.0,
        "gemini-1.5-flash": 65.0,
        "gemini-2.0-flash": 70.0,
        "claude-3-opus": 65.0,
        "claude-3-sonnet": 58.0,
        "claude-3-haiku": 42.0,
        "grok-2": 68.0,
        "grok-2-mini": 62.0,
        "command-r-plus": 55.0,
        "command-r": 45.0,
    }
    
    result = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            result[canonical] = score
    
    return result
