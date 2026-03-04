#!/usr/bin/env python3
"""
Comprehensive search for benchmark datasets on HuggingFace.
Improved version with better search queries and error handling.
"""

import json
import time
import re
from typing import List, Dict, Any
from huggingface_hub import HfApi
from datasets import get_dataset_config_names


def search_benchmark_datasets(
    queries: List[str] = None,
    limit_per_query: int = 50,
    total_limit: int = 200
) -> List[Dict[str, Any]]:
    """
    Search HuggingFace datasets for benchmarks.
    
    Args:
        queries: List of search queries
        limit_per_query: Maximum datasets per query
        total_limit: Maximum total unique datasets
        
    Returns:
        List of dataset info dicts
    """
    api = HfApi()
    
    # Expanded search queries for benchmarks
    default_queries = [
        "benchmark",
        "evaluation", 
        "leaderboard",
        "llm evaluation",
        "language model benchmark",
        "reasoning benchmark",
        "coding benchmark",
        "math benchmark",
        "question answering benchmark",
        "multimodal benchmark",
        "vision language benchmark",
        "natural language understanding",
        "commonsense reasoning",
        "mathematical reasoning",
        "code generation",
        "text generation evaluation",
        "AI evaluation",
        "model comparison",
        "performance evaluation",
        "accuracy scores",
        "pass@k",
        "human evaluation",
        "MMLU",
        "HELM",
        "BIG-bench",
        "HumanEval",
        "GSM8K",
        "ARC",
        "HellaSwag",
        "TruthfulQA",
        "DROP",
        "SQuAD",
        "RACE",
        "GLUE",
        "SuperGLUE",
    ]
    
    if queries is None:
        queries = default_queries
    
    all_datasets = []
    seen_ids = set()
    
    for query in queries:
        print(f"Searching for datasets with query: '{query}'")
        try:
            datasets = api.list_datasets(
                search=query,
                limit=limit_per_query,
                sort="downloads",  # Sort by popularity
                direction=-1
            )
            
            for dataset in datasets:
                if dataset.id in seen_ids:
                    continue
                    
                seen_ids.add(dataset.id)
                
                # Get description safely
                description = getattr(dataset, 'description', '')
                if description is None:
                    description = ''
                
                # Convert to dict
                dataset_dict = {
                    'id': dataset.id,
                    'author': dataset.author,
                    'lastModified': getattr(dataset, 'lastModified', ''),
                    'downloads': getattr(dataset, 'downloads', 0),
                    'likes': getattr(dataset, 'likes', 0),
                    'tags': getattr(dataset, 'tags', []),
                    'description': description,
                    'search_query': query
                }
                all_datasets.append(dataset_dict)
                
                if len(all_datasets) >= total_limit:
                    break
                
        except Exception as e:
            print(f"Error searching query '{query}': {e}")
        
        time.sleep(0.3)  # Rate limiting
        
        if len(all_datasets) >= total_limit:
            break
    
    # Sort by downloads (popularity)
    all_datasets.sort(
        key=lambda x: x.get('downloads', 0), 
        reverse=True
    )
    
    return all_datasets


def filter_benchmark_datasets(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter datasets to those likely containing model evaluation results.
    """
    benchmark_keywords = [
        'score', 'accuracy', 'pass@', 'eval', 'evaluation', 'benchmark',
        'leaderboard', 'performance', 'result', 'metric', 'test',
        'validation', 'human', 'judge', 'rating', 'elo', 'mmu',
        'comparison', 'ranking', 'measure', 'assessment', 'contest'
    ]
    
    filtered = []
    
    for dataset in datasets:
        description = dataset.get('description', '').lower()
        tags = [tag.lower() for tag in dataset.get('tags', [])]
        dataset_id = dataset['id'].lower()
        
        # Check if description contains benchmark keywords
        has_keyword = any(keyword in description for keyword in benchmark_keywords)
        
        # Check tags for benchmark indicators
        benchmark_tags = {'benchmark', 'evaluation', 'leaderboard', 'metrics', 'ranking'}
        has_benchmark_tag = any(tag in benchmark_tags for tag in tags)
        
        # Check if dataset name suggests benchmark
        is_benchmark_name = any(
            keyword in dataset_id for keyword in 
            ['bench', 'eval', 'score', 'leaderboard', 'performance', 'metric']
        )
        
        # Check for common benchmark names in dataset ID
        common_benchmarks = [
            'mmlu', 'gsm8k', 'arc', 'hellaswag', 'truthfulqa', 'drop',
            'squad', 'race', 'glue', 'superglue', 'bigbench', 'humaneval',
            'mbpp', 'math', 'ceval', 'cmmlu', 'mmmu', 'mmbench', 'scienceqa'
        ]
        has_benchmark_name = any(benchmark in dataset_id for benchmark in common_benchmarks)
        
        if has_keyword or has_benchmark_tag or is_benchmark_name or has_benchmark_name:
            # Calculate benchmark score (higher is better)
            benchmark_score = (
                (1 if has_keyword else 0) +
                (2 if has_benchmark_tag else 0) +
                (1 if is_benchmark_name else 0) +
                (3 if has_benchmark_name else 0)
            )
            dataset['benchmark_score'] = benchmark_score
            dataset['benchmark_reasons'] = []
            if has_keyword:
                dataset['benchmark_reasons'].append('keyword_in_description')
            if has_benchmark_tag:
                dataset['benchmark_reasons'].append('benchmark_tag')
            if is_benchmark_name:
                dataset['benchmark_reasons'].append('benchmark_name')
            if has_benchmark_name:
                dataset['benchmark_reasons'].append('known_benchmark')
            filtered.append(dataset)
    
    # Sort by benchmark score
    filtered.sort(key=lambda x: x.get('benchmark_score', 0), reverse=True)
    return filtered


def explore_dataset_structure(dataset_id: str):
    """
    Explore the structure of a dataset to understand its format.
    Returns whether the dataset contains model evaluation scores.
    """
    print(f"\n{'='*60}")
    print(f"Exploring dataset: {dataset_id}")
    print('='*60)
    
    try:
        # Get available configurations
        configs = get_dataset_config_names(dataset_id)
        print(f"Available configs: {configs}")
        
        if not configs:
            print("No configurations found")
            return False
        
        # Try to load a small sample
        from datasets import load_dataset
        
        # Try different splits
        splits_to_try = ['test', 'validation', 'train', 'default']
        
        for split in splits_to_try:
            try:
                dataset = load_dataset(
                    dataset_id, 
                    configs[0], 
                    split=split,
                    streaming=True
                )
                break
            except:
                continue
        else:
            # If no split works, try without split
            try:
                dataset = load_dataset(
                    dataset_id,
                    configs[0],
                    streaming=True
                )
            except Exception as e:
                print(f"Error loading dataset: {e}")
                return False
        
        # Get features
        features = dataset.features
        print(f"\nDataset features: {features}")
        
        # Check for score-related columns
        score_keywords = ['score', 'accuracy', 'pass', 'rating', 'elo', 'metric']
        score_columns = []
        for column in dataset.column_names:
            if any(keyword in column.lower() for keyword in score_keywords):
                score_columns.append(column)
        
        if score_columns:
            print(f"\nFound score-related columns: {score_columns}")
        
        # Look for model-related columns
        model_keywords = ['model', 'llm', 'gpt', 'claude', 'llama', 'gemini']
        model_columns = []
        for column in dataset.column_names:
            if any(keyword in column.lower() for keyword in model_keywords):
                model_columns.append(column)
        
        if model_columns:
            print(f"Found model-related columns: {model_columns}")
        
        # Check first few examples
        print(f"\nFirst 2 examples:")
        sample_count = 0
        for example in dataset:
            print(f"\n--- Example {sample_count + 1} ---")
            for key, value in example.items():
                if key in score_columns or key in model_columns:
                    # Always show score and model columns
                    if isinstance(value, (str, int, float, bool)):
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        print(f"  *{key}*: {value}")
                    elif isinstance(value, list):
                        print(f"  *{key}*: list[{len(value)}]")
                    elif isinstance(value, dict):
                        print(f"  *{key}*: dict[{len(value)} keys]")
                    else:
                        print(f"  *{key}*: {type(value).__name__}")
                elif sample_count == 0:  # Show other columns only for first example
                    if isinstance(value, (str, int, float, bool)):
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"  {key}: {value}")
                    elif isinstance(value, list):
                        print(f"  {key}: list[{len(value)}]")
                    elif isinstance(value, dict):
                        print(f"  {key}: dict[{len(value)} keys]")
            
            sample_count += 1
            if sample_count >= 2:
                break
        
        has_scores = len(score_columns) > 0
        has_models = len(model_columns) > 0
        
        print(f"\nEvaluation potential: scores={has_scores}, models={has_models}")
        return has_scores and has_models
        
    except Exception as e:
        print(f"Error exploring dataset {dataset_id}: {e}")
        return False


def main():
    """Main search and exploration."""
    print("Searching for benchmark datasets on HuggingFace...")
    print(f"Starting at: {time.ctime()}")
    
    # Search for benchmark datasets
    datasets = search_benchmark_datasets(total_limit=300)
    print(f"\nFound {len(datasets)} total datasets")
    
    # Filter to likely benchmark datasets
    benchmark_datasets = filter_benchmark_datasets(datasets)
    print(f"Found {len(benchmark_datasets)} likely benchmark datasets")
    
    # Save results
    with open('/app/provider/research/benchmark_datasets_v2.json', 'w') as f:
        json.dump(benchmark_datasets, f, indent=2, default=str)
    
    print(f"\nTop 30 benchmark datasets:")
    for i, dataset in enumerate(benchmark_datasets[:30]):
        print(f"{i+1:2d}. {dataset['id']}")
        print(f"     Score: {dataset.get('benchmark_score', 0)}, "
              f"Downloads: {dataset.get('downloads', 0):,}, "
              f"Tags: {', '.join(dataset.get('tags', [])[:3])}")
        desc = dataset.get('description', '')[:120]
        if len(desc) > 120:
            desc = desc[:117] + "..."
        if desc.strip():
            print(f"     {desc}")
        print()
    
    # Explore top promising datasets in detail
    print("\n" + "="*60)
    print("Exploring most promising benchmark datasets...")
    print("="*60)
    
    promising_datasets = []
    for dataset in benchmark_datasets[:20]:  # Check top 20
        dataset_id = dataset['id']
        
        # Skip if it's one of our existing sources
        existing_benchmarks = [
            'mmlu', 'gsm8k', 'arc', 'bbh', 'agieval', 'mathvista',
            'bigcodebench', 'humaneval', 'swebench', 'livebench',
            'livecodebench', 'scicode', 'tool_use', 'chinese',
            'ailuminate', 'megabench', 'helm', 'domain_specific', 'vision'
        ]
        
        if any(benchmark in dataset_id.lower() for benchmark in existing_benchmarks):
            print(f"\nSkipping {dataset_id} (already in existing sources)")
            continue
        
        print(f"\nEvaluating {dataset_id}...")
        is_promising = explore_dataset_structure(dataset_id)
        
        if is_promising:
            dataset['is_promising'] = True
            promising_datasets.append(dataset)
            print(f"✓ {dataset_id} looks promising for model evaluation!")
        else:
            dataset['is_promising'] = False
            print(f"✗ {dataset_id} doesn't seem to contain model evaluation scores")
        
        time.sleep(1)  # Rate limiting
    
    # Save promising datasets
    if promising_datasets:
        with open('/app/provider/research/promising_benchmarks.json', 'w') as f:
            json.dump(promising_datasets, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"Found {len(promising_datasets)} promising benchmark datasets:")
        for i, dataset in enumerate(promising_datasets):
            print(f"{i+1}. {dataset['id']}")
    
    print(f"\nSearch complete at: {time.ctime()}")
    print(f"All results saved to: /app/provider/research/")
    print(f"  - benchmark_datasets_v2.json: All filtered datasets")
    print(f"  - promising_benchmarks.json: Promising datasets with evaluation scores")


if __name__ == "__main__":
    main()