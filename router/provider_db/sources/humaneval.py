"""
HumanEval - Code generation benchmark.
Tests ability to write functional code from descriptions.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_humaneval() -> Dict[str, float]:
    """
    Fetch HumanEval scores from known results.
    Returns dict: model_id -> coding_score (0-100).
    
    HumanEval contains 164 programming problems in Python
    with function signatures, docstrings, and unit tests.
    Measures pass@1 - whether the generated code passes all tests.
    """
    scores = {}
    
    scores = _fallback_scores()
    if scores:
        print(f"HumanEval: {len(scores)} coding scores (fallback)")
        return scores
    
    print("HumanEval: no scores available")
    return {}


def _fallback_scores() -> Dict[str, float]:
    """
    Static HumanEval scores from published results and leaderboards.
    These are pass@1 rates (percentage of problems solved).
    """
    known = {
        # Top coding models (2024-2025)
        "gpt-4o": 90.0,
        "claude-3.5-sonnet": 92.0,
        "claude-3.5-sonnet-20241022": 92.0,
        "gpt-4-turbo": 85.0,
        "gpt-4": 80.0,
        "deepseek-coder-v2": 88.0,
        "deepseek-coder": 78.0,
        "deepseek-r1": 75.0,
        "qwen-2.5-coder-32b": 82.0,
        "qwen-2.5-coder": 78.0,
        "codeqwen-1.5-7b": 75.0,
        "llama-3.1-405b": 80.0,
        "llama-3.1-70b": 72.0,
        "llama-3.1-8b": 55.0,
        "mistral-large": 70.0,
        "mixtral-8x22b": 68.0,
        "starcoder-2-15b": 65.0,
        "starcoder-2": 60.0,
        "starcoder": 55.0,
        "phi-4": 72.0,
        "phi-3-medium": 58.0,
        "gemini-1.5-pro": 75.0,
        "gemini-1.5-flash": 68.0,
        "claude-3-opus": 70.0,
        "claude-3-sonnet": 62.0,
        "claude-3-haiku": 45.0,
    }
    
    result = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            result[canonical] = score
    
    return result
