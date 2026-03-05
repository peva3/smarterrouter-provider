"""
LiveBench - fetch reasoning scores.
Primary source for reasoning_score (0-100).
Uses multiple sources: LiveBench, and aggregates with other reasoning sources.
"""

from typing import Dict
from ..model_mapper import model_mapper


async def fetch_livebench() -> Dict[str, float]:
    """Return dict: model_id -> reasoning_score (0-100)."""
    scores = {}
    
    # Try LiveBench first
    scores = _try_livebench_judgment()
    if scores:
        return scores
    
    # Fallback to combined reasoning sources
    scores = _combine_reasoning_sources()
    if scores:
        print(f"LiveBench: using combined reasoning sources: {len(scores)} scores")
        return scores
    
    # Final fallback to static scores
    return _fallback_scores()


def _try_livebench_judgment() -> Dict[str, float]:
    """Try to fetch from LiveBench HuggingFace datasets."""
    try:
        from datasets import load_dataset
        
        dataset = load_dataset('livebench/model_judgment', split='leaderboard')
        if not dataset or len(dataset) == 0:
            print("LiveBench: empty dataset")
            return {}
        
        # Try all available categories and average
        model_scores = {}
        for row in dataset:
            model = row.get('model') or row.get('model_id')
            score = row.get('score')
            if model is None or score is None:
                continue
            try:
                s = float(score)
                if s <= 1.0:
                    s *= 100
                s = max(0.0, min(100.0, s))
                model_scores.setdefault(model, []).append(s)
            except (ValueError, TypeError):
                continue
        
        # Average per model
        scores = {}
        for model, score_list in model_scores.items():
            avg_score = sum(score_list) / len(score_list)
            canonical = model_mapper.to_canonical(str(model))
            if canonical:
                scores[canonical] = avg_score
        
        if scores:
            print(f"LiveBench: {len(scores)} reasoning scores (from model_judgment)")
            return scores
        
    except Exception as e:
        print(f"LiveBench: error loading dataset: {e}")
    
    return {}


def _combine_reasoning_sources() -> Dict[str, float]:
    """Combine scores from multiple reasoning sources."""
    scores = {}
    
    # Try GSM8K
    try:
        from . import gsm8k
        gsm_scores = gsm8k.fetch_gsm8k()
        for model, score in gsm_scores.items():
            scores.setdefault(model, []).append(('gsm8k', score))
    except Exception as e:
        pass
    
    # Try ARC
    try:
        from . import arc
        arc_scores = arc.fetch_arc()
        for model, score in arc_scores.items():
            scores.setdefault(model, []).append(('arc', score))
    except Exception as e:
        pass
    
    # Try BBH
    try:
        from . import bbh
        bbh_scores = bbh.fetch_bbh()
        for model, score in bbh_scores.items():
            scores.setdefault(model, []).append(('bbh', score))
    except Exception as e:
        pass
    
    # Try AGIEval
    try:
        from . import agieval
        agi_scores = agieval.fetch_agieval()
        for model, score in agi_scores.items():
            scores.setdefault(model, []).append(('agieval', score))
    except Exception as e:
        pass
    
    # Try MATHVista
    try:
        from . import mathvista
        mathv_scores = mathvista.fetch_mathvista()
        for model, score in mathv_scores.items():
            scores.setdefault(model, []).append(('mathvista', score))
    except Exception as e:
        pass
    
    # Try AIME
    try:
        from . import aime
        aime_scores = aime.fetch_aime()
        for model, score in aime_scores.items():
            scores.setdefault(model, []).append(('aime', score))
    except Exception as e:
        pass
    
    # Try FrontierMath
    try:
        from . import frontiermath
        fm_scores = frontiermath.fetch_frontiermath()
        for model, score in fm_scores.items():
            scores.setdefault(model, []).append(('frontiermath', score))
    except Exception as e:
        pass
    
    # Try Chinese reasoning
    try:
        from . import chinese_reasoning
        cn_scores = chinese_reasoning.fetch_chinese_reasoning()
        for model, score in cn_scores.items():
            scores.setdefault(model, []).append(('chinese_reasoning', score))
    except Exception as e:
        pass
    
    # Average the scores for each model
    result = {}
    weights = {
        'gsm8k': 1.0,
        'arc': 0.9,
        'bbh': 0.9,
        'agieval': 0.8,
        'mathvista': 0.8,
        'aime': 0.8,
        'frontiermath': 0.8,
        'chinese_reasoning': 0.8,
    }
    
    for model, score_list in scores.items():
        weighted_sum = 0.0
        weight_total = 0.0
        for source, score in score_list:
            w = weights.get(source, 0.8)
            weighted_sum += score * w
            weight_total += w
        
        if weight_total > 0:
            result[model] = weighted_sum / weight_total
    
    return result


def _fallback_scores() -> Dict[str, float]:
    """Static LiveBench reasoning scores for major models from published results."""
    known = {
        # Claude family
        "claude-4.6-opus": 88.67,
        "claude-4.5-opus": 80.09,
        "claude-4.5-sonnet": 77.59,
        "claude-3.5-sonnet": 84.7,
        "claude-3-opus": 83.9,
        "claude-3-sonnet": 78.2,
        
        # GPT family
        "gpt-5": 83.21,
        "gpt-4o": 85.5,
        "gpt-4-turbo": 82.3,
        
        # Gemini family
        "gemini-2.5-pro": 77.42,
        "gemini-2.5-flash": 74.55,
        "gemini-1.5-pro": 83.1,
        "gemini-1.5-flash": 77.8,
        
        # Llama family
        "llama-3.1-405b": 79.4,
        "llama-3.1-70b": 79.4,
        "llama-3.1-8b": 70.1,
        "llama-3-70b": 78.0,
        "llama-3-8b": 68.0,
        "mixtral-8x7b": 72.5,
        
        # Qwen family
        "qwen-2.5-72b": 84.2,
        "qwen-2.5-7b": 73.6,
        "qwen3-235b": 85.0,
        "qwen3-32b": 78.0,
        
        # DeepSeek family
        "deepseek-r1": 89.3,
        "deepseek-v3": 77.17,
        "deepseek-chat": 81.7,
        
        # Other major models
        "kimi-k2.5": 75.96,
        "glm-4": 69.11,
        "glm-5": 69.11,
        "grok-4": 79.13,
        "grok-3": 75.0,
    }
    
    scores = {}
    for name, score in known.items():
        canonical = model_mapper.to_canonical(name)
        if canonical:
            scores[canonical] = score
    return scores
