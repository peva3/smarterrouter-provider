"""
bigcode/bigcodebench-results - fetch coding scores.
BigCodeBench benchmark results with pass@k scores
"""

from typing import Dict
try:
    from datasets import load_dataset
except ImportError:
    load_dataset = None

from router.provider_db.model_mapper import model_mapper

def fetch_bigcodebench_results() -> Dict[str, float]:
    """Fetch coding scores from bigcode/bigcodebench-results."""
    scores = {}
    
    if load_dataset is None:
        print(f"bigcode/bigcodebench-results: datasets library not installed")
        return scores
    
    try:
        # Load dataset
        dataset = load_dataset('bigcode/bigcodebench-results', split='test')
        
        # Parse scores - adjust field names based on actual dataset
        for item in dataset:
            model = item.get('model') or item.get('model_name') or item.get('model_id')
            score_value = item.get('accuracy') or item.get('score') or item.get('pass@1')
            
            if model and score_value is not None:
                canonical = model_mapper.to_canonical(str(model))
                if canonical:
                    # Convert 0-1 to 0-100 if needed
                    score = float(score_value)
                    if score <= 1.0:
                        score *= 100
                    # Clamp to 0-100 range
                    score = max(0.0, min(100.0, score))
                    scores[canonical] = score
        
        print(f"bigcode/bigcodebench-results: fetched {len(scores)} coding scores")
        
    except Exception as e:
        print(f"bigcode/bigcodebench-results failed: {e}")
    
    return scores