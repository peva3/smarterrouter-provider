"""
Open LLM Leaderboard Results - fetch benchmark scores.
Source: https://huggingface.co/datasets/open-llm-leaderboard/results

This dataset contains model evaluation results from the Open LLM Leaderboard,
including benchmarks like IFEval, MMLU-Pro, BBH, GPQA, MATH, MuSR, and more.

Category mapping:
- IFEval -> general (instruction following)
- MMLU-Pro -> general
- BBH -> reasoning
- GPQA -> reasoning
- MATH (hard) -> reasoning
- MuSR -> reasoning
"""

from typing import Dict
from ..model_mapper import model_mapper


BENCHMARK_CATEGORIES = {
    'leaderboard_ifeval': 'general',
    'leaderboard_mmlu_pro': 'general',
    'leaderboard': 'general',  # Default MMLU
    'leaderboard_bbh': 'reasoning',
    'leaderboard_gpqa': 'reasoning',
    'leaderboard_math_hard': 'reasoning',
    'leaderboard_musr': 'reasoning',
}


async def fetch_open_llm_leaderboard() -> Dict[str, float]:
    """
    Fetch benchmark scores from Open LLM Leaderboard results dataset.
    Returns dict: model_id -> score based on benchmark.
    """
    scores = {}
    
    try:
        from datasets import load_dataset
        
        # Load with streaming to avoid parquet errors
        ds = load_dataset('open-llm-leaderboard/results', split='train', streaming=True)
        
        # Track scores by benchmark
        benchmark_scores = {k: {} for k in BENCHMARK_CATEGORIES.keys()}
        
        count = 0
        for row in ds:
            count += 1
            model = row.get('model_name') or row.get('model_id')
            if not model:
                continue
            
            # Get results - it's in the 'results' field, not 'leaderboard'
            results = row.get('results', {})
            if not results:
                continue
            
            # Extract scores for each benchmark we track
            for bench_key, category in BENCHMARK_CATEGORIES.items():
                if bench_key in results:
                    bench_data = results[bench_key]
                    
                    if isinstance(bench_data, dict):
                        # Look for the score field
                        score = None
                        
                        # Try different field names based on benchmark
                        if bench_key == 'leaderboard_ifeval':
                            for field in ['inst_level_strict_acc', 'inst_level_loose_acc', 'acc']:
                                key = f'{field},none'
                                if key in bench_data:
                                    try:
                                        score = float(bench_data[key])
                                        break
                                    except (ValueError, TypeError):
                                        continue
                        elif bench_key in ['leaderboard_bbh', 'leaderboard_gpqa', 'leaderboard_musr']:
                            for field in ['acc_norm', 'acc']:
                                key = f'{field},none'
                                if key in bench_data:
                                    try:
                                        score = float(bench_data[key])
                                        break
                                    except (ValueError, TypeError):
                                        continue
                        else:
                            # Default: try acc or acc_norm
                            for field in ['acc,none', 'acc_norm,none', 'exact_match,none']:
                                if field in bench_data:
                                    try:
                                        score = float(bench_data[field])
                                        break
                                    except (ValueError, TypeError):
                                        continue
                        
                        if score is not None:
                            if score <= 1.0:
                                score *= 100
                            score = max(0.0, min(100.0, score))
                            
                            canonical = model_mapper.to_canonical(str(model))
                            if canonical:
                                benchmark_scores[bench_key][canonical] = score
        
        print(f"OpenLLM: processed {count} rows")
        
        # Report what we found
        for bench_key, bench_scores in benchmark_scores.items():
            if bench_scores:
                category = BENCHMARK_CATEGORIES.get(bench_key, 'unknown')
                print(f"OpenLLM {bench_key}: {len(bench_scores)} {category} scores")
        
        # Return IFEval scores as general (instruction following is important)
        if benchmark_scores.get('leaderboard_ifeval'):
            return benchmark_scores['leaderboard_ifeval']
        
        # Fallback to MMLU-Pro
        if benchmark_scores.get('leaderboard_mmlu_pro'):
            return benchmark_scores['leaderboard_mmlu_pro']
        
        # Fallback to general leaderboard
        if benchmark_scores.get('leaderboard'):
            return benchmark_scores['leaderboard']
        
    except ImportError:
        print("OpenLLM: 'datasets' library not installed")
    except Exception as e:
        print(f"OpenLLM: error loading dataset: {e}")
    
    # Fallback to empty
    return {}
