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
            ("bigcode/bigcodebench", "test"),
        ]
        
        for ds_name, split in datasets_to_try:
            try:
                ds = load_dataset(ds_name, split=split)
                if ds and len(ds) > 0:
                    scores = _extract_scores(ds)
                    if scores:
                        print(f"BigCodeBench: {len(scores)} coding scores ({ds_name})")
                        return scores
            except Exception:
                continue
        
    except ImportError:
        print("BigCodeBench: 'datasets' library not installed")
    except Exception as e:
        print(f"BigCodeBench: {e}")
    
    print("BigCodeBench: failed to fetch")
    return {}


def _extract_scores(dataset) -> Dict[str, float]:
    """Extract model -> coding score from dataset."""
    scores = {}
    
    # Check column names
    columns = getattr(dataset, 'column_names', [])
    model_col = next((c for c in columns if "model" in c.lower()), None)
    score_col = next((c for c in columns if any(s in c.lower() for s in ["score", "pass", "accuracy"])), None)
    
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
            score = item.get("score") or item.get("pass_rate") or item.get("pass@1")
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
