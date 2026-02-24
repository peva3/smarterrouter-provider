#!/usr/bin/env python3
"""
Comprehensive search for benchmark datasets on HuggingFace.
Finds datasets with evaluation results for LLMs.
"""

import json
import time
import re
from typing import List, Dict, Any
from huggingface_hub import HfApi
from datasets import get_dataset_config_names


def search_benchmark_datasets(
    queries: List[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search HuggingFace datasets for benchmarks.
    
    Args:
        queries: List of search queries
        limit: Maximum number of datasets to return
        
    Returns:
        List of dataset info dicts
    """
    api = HfApi()
    
    # Common benchmark search queries
    default_queries = [
        "benchmark", "evaluation", "leaderboard", 
        "llm evaluation", "language model benchmark",
        "reasoning benchmark", "coding benchmark", "math benchmark",
        "question answering", "multimodal benchmark", "vision language"
    ]
    
    if queries is None:
        queries = default_queries
    
    all_datasets = []
    
    for query in queries:
        print(f"Searching for datasets with query: '{query}'")
        try:
            datasets = api.list_datasets(
                search=query,
                limit=50,
                sort="lastModified",
                direction=-1
            )
            
            for dataset in datasets:
                # Check if dataset already collected
                if any(d['id'] == dataset.id for d in all_datasets):
                    continue
                    
                # Convert to dict and add query
                dataset_dict = {
                    'id': dataset.id,
                    'author': dataset.author,
                    'lastModified': dataset.lastModified,
                    'downloads': dataset.downloads,
                    'likes': dataset.likes,
                    'tags': dataset.tags or [],
                    'description': dataset.description or '',
                    'search_query': query
                }
                all_datasets.append(dataset_dict)
                
        except Exception as e:
            print(f"Error searching query '{query}': {e}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Sort by downloads + likes (popularity)
    all_datasets.sort(
        key=lambda x: (x.get('downloads', 0) + x.get('likes', 0) * 10), 
        reverse=True
    )
    
    return all_datasets[:limit]


def filter_benchmark_datasets(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter datasets to those likely containing model evaluation results.
    """
    benchmark_keywords = [
        'score', 'accuracy', 'pass@', 'eval', 'evaluation', 'benchmark',
        'leaderboard', 'performance', 'result', 'metric', 'test',
        'validation', 'human', 'judge', 'rating', 'elo', 'mmu'
    ]
    
    filtered = []
    
    for dataset in datasets:
        description = dataset.get('description', '').lower()
        tags = [tag.lower() for tag in dataset.get('tags', [])]
        
        # Check if description contains benchmark keywords
        has_keyword = any(keyword in description for keyword in benchmark_keywords)
        
        # Check tags for benchmark indicators
        benchmark_tags = {'benchmark', 'evaluation', 'leaderboard', 'metrics'}
        has_benchmark_tag = any(tag in benchmark_tags for tag in tags)
        
        # Check if dataset name suggests benchmark
        dataset_id = dataset['id'].lower()
        is_benchmark_name = any(
            keyword in dataset_id for keyword in 
            ['bench', 'eval', 'score', 'leaderboard', 'performance']
        )
        
        if has_keyword or has_benchmark_tag or is_benchmark_name:
            dataset['benchmark_score'] = (
                (1 if has_keyword else 0) +
                (2 if has_benchmark_tag else 0) +
                (1 if is_benchmark_name else 0)
            )
            filtered.append(dataset)
    
    # Sort by benchmark score
    filtered.sort(key=lambda x: x.get('benchmark_score', 0), reverse=True)
    return filtered


def explore_dataset_structure(dataset_id: str):
    """
    Explore the structure of a dataset to understand its format.
    """
    print(f"\n{'='*60}")
    print(f"Exploring dataset: {dataset_id}")
    print('='*60)
    
    try:
        # Get available configurations
        configs = get_dataset_config_names(dataset_id)
        print(f"Available configs: {configs}")
        
        # Try to load a small sample from first config
        if configs:
            from datasets import load_dataset
            try:
                dataset = load_dataset(
                    dataset_id, 
                    configs[0], 
                    split='test',
                    trust_remote_code=True,
                    streaming=True
                )
                
                # Get first few examples
                print(f"\nDataset features: {dataset.features}")
                
                sample_count = 0
                for example in dataset:
                    print(f"\n--- Example {sample_count + 1} ---")
                    for key, value in example.items():
                        if isinstance(value, (str, int, float, bool)):
                            # Truncate long values
                            if isinstance(value, str) and len(value) > 200:
                                value = value[:200] + "..."
                            print(f"  {key}: {value}")
                        elif isinstance(value, list):
                            print(f"  {key}: list[{len(value)}]")
                        elif isinstance(value, dict):
                            print(f"  {key}: dict[{len(value)} keys]")
                        else:
                            print(f"  {key}: {type(value).__name__}")
                    
                    sample_count += 1
                    if sample_count >= 2:
                        break
                        
            except Exception as e:
                print(f"Error loading dataset: {e}")
                
    except Exception as e:
        print(f"Error exploring dataset {dataset_id}: {e}")


def main():
    """Main search and exploration."""
    print("Searching for benchmark datasets on HuggingFace...")
    
    # Search for benchmark datasets
    datasets = search_benchmark_datasets(limit=100)
    print(f"Found {len(datasets)} total datasets")
    
    # Filter to likely benchmark datasets
    benchmark_datasets = filter_benchmark_datasets(datasets)
    print(f"Found {len(benchmark_datasets)} likely benchmark datasets")
    
    # Save results
    with open('/app/provider/research/benchmark_datasets.json', 'w') as f:
        json.dump(benchmark_datasets, f, indent=2, default=str)
    
    print(f"\nTop 20 benchmark datasets:")
    for i, dataset in enumerate(benchmark_datasets[:20]):
        print(f"{i+1:2d}. {dataset['id']}")
        print(f"     Downloads: {dataset.get('downloads', 0):,}, "
              f"Likes: {dataset.get('likes', 0)}, "
              f"Tags: {', '.join(dataset.get('tags', [])[:3])}")
        desc = dataset.get('description', '')[:150]
        if len(desc) > 150:
            desc = desc[:147] + "..."
        print(f"     {desc}")
        print()
    
    # Explore top 5 datasets in detail
    print("\n" + "="*60)
    print("Exploring top 5 benchmark datasets in detail...")
    print("="*60)
    
    for i, dataset in enumerate(benchmark_datasets[:5]):
        explore_dataset_structure(dataset['id'])
        time.sleep(2)  # Rate limiting
    
    print("\nSearch complete!")
    print(f"Results saved to: /app/provider/research/benchmark_datasets.json")


if __name__ == "__main__":
    main()