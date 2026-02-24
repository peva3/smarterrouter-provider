"""
MMLU (Massive Multitask Language Understanding) - fetch general knowledge scores.
Primary source for general_score (0-100).
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_mmlu() -> Dict[str, float]:
    """
    Fetch MMLU scores from HuggingFace or static leaderboard.
    Returns dict: model_id -> general_score (0-100).
    """
    scores = {}
    
    try:
        from datasets import load_dataset
        
        datasets_to_try = [
            ("cais/mmlu", "test"),
        ]
        
        for ds_name, split in datasets_to_try:
            try:
                ds = load_dataset(ds_name, split=split)
                if ds and len(ds) > 0:
                    scores = _extract_scores(ds)
                    if scores:
                        print(f"MMLU: {len(scores)} general scores ({ds_name})")
                        return scores
            except Exception:
                continue
        
    except ImportError:
        print("MMLU: 'datasets' library not installed")
    except Exception as e:
        print(f"MMLU: {e}")
    
    # Fallback: use hardcoded scores from paperswithcode, etc.
    scores = _fallback_scores()
    if scores:
        print(f"MMLU: {len(scores)} general scores (static)")
        return scores
    
    print("MMLU: failed to fetch")
    return {}


def _extract_scores(dataset) -> Dict[str, float]:
    scores = {}
    columns = getattr(dataset, 'column_names', [])
    model_col = next((c for c in columns if "model" in c.lower()), None)
    acc_col = next((c for c in columns if any(s in c.lower() for s in ["accuracy", "score", "mmlu"])), None)
    
    if model_col and acc_col:
        for item in dataset:
            name = item.get(model_col)
            acc = item.get(acc_col)
            if name and acc is not None:
                try:
                    a = float(acc)
                    if a > 1 and a <= 100:
                        a = a  # percentage
                    elif a <= 1:
                        a = a * 100
                    a = max(0.0, min(100.0, a))
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = a
                except (ValueError, TypeError):
                    continue
    return scores


def _fallback_scores() -> Dict[str, float]:
    """Static MMLU scores for major models from published results."""
    known = {
        "gpt-4": 86.4,
        "gpt-4-turbo": 85.8,
        "gpt-3.5-turbo": 70.0,
        "claude-3-opus": 86.8,
        "claude-3-sonnet": 79.7,
        "claude-3-haiku": 75.2,
        "claude-3.5-sonnet": 85.0,
        "gemini-1.5-pro": 85.9,
        "gemini-1.5-flash": 78.9,
        "llama-3.1-70b": 81.6,
        "llama-3.1-8b": 73.3,
        "llama-3-70b": 77.2,
        "llama-3-8b": 68.9,
        "mixtral-8x7b": 71.4,
        "qwen-2.5-72b": 87.5,
        "qwen-2.5-7b": 74.6,
        "deepseek-r1": 90.0,
        "deepseek-chat": 84.0,
    }
    
    scores = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = score
    return scores
