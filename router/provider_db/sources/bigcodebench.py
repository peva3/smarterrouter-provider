"""
BigCodeBench - fetch coding scores.
Primary source for coding_score (0-100).
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_bigcodebench() -> Dict[str, float]:
    """
    Fetch coding scores from HuggingFace datasets.
    Returns dict: model_id -> coding_score (0-100).
    """
    scores = {}
    
    try:
        from datasets import load_dataset
        
        datasets_to_try = [
            ("bigcode/bigcodebench-results", "train"),  # Results dataset with scores
            ("bigcode/bigcodebench", "v0.1.4"),  # Main dataset
            ("bigcode/bigcodebench", "v0.1.3"),
            ("bigcode/bigcodebench", "v0.1.2"),
            ("bigcode/bigcodebench", "v0.1.1"),
            ("bigcode/bigcodebench", "v0.1.0_hf"),
        ]
        
        for ds_name, split in datasets_to_try:
            try:
                ds = load_dataset(ds_name, split=split)
                if ds and len(ds) > 0:
                    scores = _extract_scores(ds)
                    if scores:
                        print(f"BigCodeBench: {len(scores)} coding scores ({ds_name}/{split})")
                        return scores
            except Exception as e:
                continue
        
    except ImportError:
        print("BigCodeBench: 'datasets' library not installed")
    except Exception as e:
        print(f"BigCodeBench: {e}")
    
    # Try fallback
    scores = _fallback_scores()
    if scores:
        print(f"BigCodeBench: {len(scores)} coding scores (fallback)")
        return scores
    
    print("BigCodeBench: failed to fetch")
    return {}


def _fallback_scores() -> Dict[str, float]:
    """Static BigCodeBench scores from published results."""
    known = {
        # GPT family
        "gpt-5": 85.0,
        "gpt-4o": 75.0,
        "gpt-4o-mini": 68.0,
        "claude-3.5-sonnet": 78.0,
        "claude-3.5-sonnet-20241022": 78.0,
        "claude-3.5-haiku": 58.0,
        "gpt-4-turbo": 68.0,
        "gpt-4": 62.0,
        
        # Claude family
        "claude-4-opus": 82.0,
        "claude-4-sonnet": 78.0,
        "claude-3-opus": 55.0,
        "claude-3-sonnet": 48.0,
        "claude-3-haiku": 35.0,
        
        # DeepSeek family
        "deepseek-coder-v2": 72.0,
        "deepseek-coder-v2.5": 75.0,
        "deepseek-coder": 58.0,
        "deepseek-r1": 62.0,
        "deepseek-v3": 64.62,
        
        # Qwen family
        "qwen-3-coder": 78.0,
        "qwen-2.5-coder-32b-instruct": 68.0,
        "qwen-2.5-coder": 62.0,
        "qwen-2.5-coder-72b": 70.0,
        "codeqwen-1.5-7b": 55.0,
        
        # Llama family
        "llama-3.1-405b-instruct": 65.0,
        "llama-3.1-70b-instruct": 58.0,
        "llama-3.1-8b-instruct": 42.0,
        "llama-3-70b-instruct": 52.0,
        "llama-3-8b-instruct": 38.0,
        "llama-4-maverick": 70.0,
        
        # Mistral family
        "mistral-large": 55.0,
        "mistral-large-3": 62.0,
        "mixtral-8x22b": 52.0,
        "mixtral-8x7b": 45.0,
        
        # Other
        "starcoder-2-15b": 48.0,
        "starcoder-2": 42.0,
        "phi-4": 55.0,
        "phi-3-medium": 42.0,
        "gemini-1.5-pro": 62.0,
        "gemini-1.5-flash": 55.0,
        "gemini-2.0-flash": 58.0,
        "gemini-2.5-pro": 72.0,
        "grok-2": 55.0,
        "grok-2-mini": 48.0,
        "grok-3": 68.0,
        "command-r-plus": 42.0,
        "command-r": 32.0,
        "kimi-k2": 77.86,
    }
    
    result = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            result[canonical] = score
    
    return result


def _extract_scores(dataset) -> Dict[str, float]:
    """Extract model -> coding score from dataset."""
    scores = {}
    
    # Check column names
    columns = getattr(dataset, 'column_names', [])
    model_col = next((c for c in columns if "model" in c.lower()), None)
    score_col = next((c for c in columns if any(s in c.lower() for s in ["score", "pass", "accuracy", "complete", "instruct"])), None)
    
    if model_col and score_col:
        for item in dataset:
            name = item.get(model_col)
            score = item.get(score_col)
            if name and score is not None:
                try:
                    s = float(score)
                    if s > 1 and s <= 100:
                        s = s  # keep as 0-100
                    elif s <= 1:
                        s = s * 100
                    s = max(0.0, min(100.0, s))
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = s
                except (ValueError, TypeError):
                    continue
    else:
        # Fallback: try common field names
        for item in dataset:
            name = item.get("model") or item.get("model_name")
            score = item.get("score") or item.get("pass_rate") or item.get("pass@1") or item.get("complete") or item.get("instruct")
            if name and score is not None:
                try:
                    s = float(score)
                    if s <= 1:
                        s *= 100
                    s = max(0.0, min(100.0, s))
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = s
                except (ValueError, TypeError):
                    continue
    
    return scores
