#!/usr/bin/env python3
"""
Search for Chinese-specific benchmark datasets on HuggingFace.
"""

import json
import time
from typing import List, Dict, Any
from huggingface_hub import HfApi


def search_chinese_benchmarks(limit_per_query: int = 100) -> List[Dict[str, Any]]:
    """
    Search for Chinese benchmark datasets.
    """
    api = HfApi()
    
    # Chinese benchmark search queries
    chinese_queries = [
        "chinese benchmark",
        "chinese evaluation",
        "中文评估",
        "中文评测",
        "中文基准",
        "C-Eval",
        "C-MMLU",
        "Gaokao benchmark",
        "Chinese math",
        "中文数学",
        "Chinese coding",
        "中文编程",
        "Chinese reasoning",
        "中文推理",
        "Chinese language model",
        "中文大模型",
        "Chinese QA",
        "中文问答",
        "Chinese knowledge",
        "中文知识",
        "multilingual Chinese",
        "Chinese multilingual",
        "CLUE",  # Chinese Language Understanding Evaluation
        "TAL-SCQ",
        "CMATH",
        "Chinese HumanEval",
        "MBPP-CN",
        "Chinese programming",
        "Chinese chatbot arena",
        "中文聊天机器人评测",
    ]
    
    all_datasets = []
    seen_ids = set()
    
    for query in chinese_queries:
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
                    'author': getattr(dataset, 'author', ''),
                    'lastModified': str(getattr(dataset, 'lastModified', '')),
                    'downloads': getattr(dataset, 'downloads', 0),
                    'likes': getattr(dataset, 'likes', 0),
                    'tags': getattr(dataset, 'tags', []),
                    'description': description,
                    'search_query': query
                }
                
                all_datasets.append(dataset_dict)
                
                # Throttle to avoid rate limiting
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error searching query '{query}': {e}")
            continue
    
    print(f"Total unique Chinese benchmark datasets found: {len(all_datasets)}")
    return all_datasets


def filter_benchmark_datasets(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter datasets to identify actual benchmarks.
    """
    benchmark_keywords = [
        'benchmark', 'evaluation', 'leaderboard', '评估', '评测', '基准',
        'accuracy', 'score', 'performance', 'metric', 'results', '排行榜',
        'ceval', 'cmmlu', 'gaokao', '数学', '编程', '代码'
    ]
    
    filtered = []
    for dataset in datasets:
        dataset_id = dataset['id'].lower()
        description = dataset.get('description', '').lower()
        tags = [tag.lower() for tag in dataset.get('tags', [])]
        
        # Check if it looks like a benchmark dataset
        is_benchmark = False
        for keyword in benchmark_keywords:
            if (keyword in dataset_id or 
                keyword in description or 
                any(keyword in tag for tag in tags)):
                is_benchmark = True
                break
        
        if is_benchmark:
            # Score the dataset based on relevance
            score = 0
            if any(kw in dataset_id for kw in ['ceval', 'cmmlu', 'gaokao']):
                score += 3
            if 'chinese' in dataset_id or '中文' in dataset_id:
                score += 2
            if any(kw in dataset_id for kw in ['math', '数学', 'coding', '编程', 'code', '代码']):
                score += 2
            if 'benchmark' in dataset_id or '评估' in dataset_id or '评测' in dataset_id:
                score += 1
                
            dataset['benchmark_score'] = score
            filtered.append(dataset)
    
    # Sort by benchmark score
    filtered.sort(key=lambda x: x.get('benchmark_score', 0), reverse=True)
    
    print(f"Filtered to {len(filtered)} Chinese benchmark datasets")
    return filtered


def main():
    """Main execution function."""
    print("=" * 80)
    print("Searching for Chinese benchmark datasets on HuggingFace")
    print("=" * 80)
    
    # Search for Chinese benchmarks
    datasets = search_chinese_benchmarks(limit_per_query=50)
    
    # Filter to actual benchmarks
    benchmarks = filter_benchmark_datasets(datasets)
    
    # Save results
    output_file = "/app/provider/research/chinese_benchmarks.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(benchmarks, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {output_file}")
    
    # Print top results
    print("\nTop Chinese benchmark datasets:")
    for i, dataset in enumerate(benchmarks[:20]):
        score = dataset.get('benchmark_score', 0)
        print(f"{i+1:2d}. [{score}] {dataset['id']}")
        print(f"     Query: {dataset.get('search_query', '')}")
        desc = dataset.get('description', '')[:150]
        if desc:
            print(f"     Desc: {desc}...")
        print()


if __name__ == "__main__":
    main()