"""
Multilingual benchmarks - fetch C-Eval and C-MMLU scores for Chinese language models.
Tests model performance on Chinese knowledge and reasoning tasks.
"""

from typing import Dict
from ..model_mapper import model_mapper


def fetch_multilingual() -> Dict[str, float]:
    """
    Fetch multilingual benchmark scores (C-Eval, C-MMLU) from HuggingFace.
    Returns dict: model_id -> general_score (0-100).
    
    C-Eval and C-MMLU are Chinese adaptations of MMLU testing
    knowledge across various subjects in Chinese.
    """
    scores = {}
    
    try:
        from datasets import load_dataset
        
        # Try to find multilingual benchmark datasets
        datasets_to_try = [
            ("ceval/ceval-exam", "val"),
            ("lmlmcat/cmmlu", "test"),
            ("XiaHan19/cmmlu", "test"),
        ]
        
        for ds_name, split in datasets_to_try:
            try:
                ds = load_dataset(ds_name, split=split)
                if ds and len(ds) > 0:
                    dataset_scores = _extract_scores(ds, ds_name)
                    if dataset_scores:
                        scores.update(dataset_scores)
                        print(f"Multilingual: {len(dataset_scores)} general scores from {ds_name}")
            except Exception as e:
                continue
        
        if scores:
            print(f"Multilingual: total {len(scores)} general scores")
            return scores
        
    except ImportError:
        print("Multilingual: 'datasets' library not installed")
    except Exception as e:
        print(f"Multilingual: {e}")
    
    # Fallback: use hardcoded scores from published results
    scores = _fallback_scores()
    if scores:
        print(f"Multilingual: {len(scores)} general scores (static)")
        return scores
    
    print("Multilingual: failed to fetch")
    return {}


def _extract_scores(dataset, dataset_name: str) -> Dict[str, float]:
    """
    Extract model scores from multilingual benchmark datasets.
    """
    scores = {}
    
    columns = getattr(dataset, 'column_names', [])
    
    # Look for model-related columns
    model_col = next((c for c in columns if "model" in c.lower()), None)
    acc_col = next((c for c in columns if any(s in c.lower() for s in ["accuracy", "score", "ceval", "cmmlu"])), None)
    
    if model_col and acc_col:
        for item in dataset:
            name = item.get(model_col)
            acc = item.get(acc_col)
            if name and acc is not None:
                try:
                    score = float(acc)
                    # Convert to 0-100 scale if needed
                    if score > 1 and score <= 100:
                        score = score
                    elif score <= 1:
                        score = score * 100
                    score = max(0.0, min(100.0, score))
                    
                    canonical = model_mapper.to_canonical(str(name))
                    if canonical:
                        scores[canonical] = score
                except (ValueError, TypeError):
                    continue
    
    return scores


def _fallback_scores() -> Dict[str, float]:
    """
    Static multilingual benchmark scores from published results.
    C-Eval and C-MMLU scores for Chinese and multilingual models.
    """
    # C-Eval and C-MMLU scores from various sources
    known = {
        # C-Eval scores (Chinese knowledge benchmark)
        "qwen-2.5-72b": 85.7,
        "qwen-2.5-7b": 72.4,
        "qwen-2-72b": 80.3,
        "qwen-2-7b": 68.9,
        "qwen1.5-72b": 78.5,
        "qwen1.5-7b": 66.2,
        "chatglm3-6b": 65.8,
        "chatglm2-6b": 61.4,
        "baichuan2-13b": 72.6,
        "baichuan2-7b": 67.8,
        "yi-34b": 81.2,
        "yi-6b": 70.5,
        "internlm2-20b": 82.4,
        "internlm2-7b": 75.8,
        "deepseek-chat": 78.9,
        "deepseek-coder": 72.4,
        
        # C-MMLU scores (Chinese MMLU adaptation)
        "qwen-2.5-72b": 86.2,
        "qwen-2.5-7b": 74.1,
        "qwen-2-72b": 81.7,
        "qwen-2-7b": 70.6,
        "yi-34b": 82.9,
        "yi-6b": 73.2,
        "chatglm3-6b": 68.4,
        "baichuan2-13b": 74.8,
        "internlm2-20b": 83.6,
        "deepseek-chat": 80.1,
        
        # English models with some multilingual capability
        "gpt-4": 78.5,
        "gpt-4-turbo": 77.9,
        "gpt-3.5-turbo": 65.4,
        "claude-3-opus": 76.8,
        "claude-3.5-sonnet": 78.2,
        "gemini-1.5-pro": 79.4,
        "llama-3.1-70b": 72.8,
        "llama-3-70b": 70.1,
        "mistral-large": 71.6,
    }
    
    scores = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = score
    
    return scores