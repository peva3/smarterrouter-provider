#!/usr/bin/env python3
"""
Analyze benchmark datasets found in search.
"""

import json
from collections import Counter
import re


def load_datasets():
    """Load benchmark datasets from file."""
    with open('/app/provider/research/benchmark_datasets_v2.json', 'r') as f:
        return json.load(f)


def analyze_categories(datasets):
    """Analyze benchmark categories based on names and tags."""
    categories = Counter()
    
    # Common category patterns
    category_patterns = {
        'math': ['math', 'mathematical', 'arithmetic', 'algebra', 'calculus'],
        'coding': ['code', 'programming', 'software', 'human', 'eval', 'swe', 'mbpp'],
        'reasoning': ['reasoning', 'logic', 'deductive', 'inductive'],
        'qa': ['qa', 'question', 'answer', 'squad', 'race', 'drop'],
        'multimodal': ['multimodal', 'vision', 'image', 'video', 'visual'],
        'language': ['language', 'linguistic', 'translation', 'glue', 'superglue'],
        'science': ['science', 'biology', 'chemistry', 'physics', 'medical'],
        'safety': ['safety', 'alignment', 'toxicity', 'harmful'],
        'commonsense': ['commonsense', 'hellaswag', 'winogrande', 'piqa'],
        'knowledge': ['knowledge', 'factual', 'trivia', 'world'],
        'multilingual': ['multilingual', 'language', 'translation', 'xglue'],
        'domain': ['domain', 'specific', 'legal', 'financial', 'medical']
    }
    
    for dataset in datasets:
        dataset_id = dataset['id'].lower()
        description = dataset.get('description', '').lower()
        tags = [tag.lower() for tag in dataset.get('tags', [])]
        
        # Check each category
        for category, keywords in category_patterns.items():
            # Check in dataset ID
            if any(keyword in dataset_id for keyword in keywords):
                categories[category] += 1
                continue
                
            # Check in description
            if any(keyword in description for keyword in keywords):
                categories[category] += 1
                continue
                
            # Check in tags
            if any(keyword in ' '.join(tags) for keyword in keywords):
                categories[category] += 1
    
    return categories


def identify_missing_benchmarks(datasets, existing_sources):
    """
    Identify benchmark datasets that are not in existing sources.
    
    Args:
        datasets: List of benchmark datasets
        existing_sources: List of existing source names
        
    Returns:
        List of missing benchmark datasets
    """
    existing_lower = [source.lower() for source in existing_sources]
    
    missing = []
    
    for dataset in datasets:
        dataset_id = dataset['id'].lower()
        
        # Check if this benchmark is already covered
        is_covered = False
        for existing in existing_lower:
            # Check if existing source name appears in dataset ID
            if existing in dataset_id:
                is_covered = True
                break
        
        if not is_covered:
            # Also check for known benchmark names that might be covered
            known_benchmarks = [
                'mmlu', 'gsm8k', 'arc', 'bbh', 'agieval', 'mathvista',
                'bigcodebench', 'humaneval', 'swebench', 'livebench',
                'livecodebench', 'scicode', 'tool_use', 'chinese',
                'ailuminate', 'megabench', 'helm', 'domain_specific', 'vision',
                'frontiermath', 'aime', 'stateval', 'gpqa', 'aider'
            ]
            
            has_known_benchmark = any(benchmark in dataset_id for benchmark in known_benchmarks)
            if not has_known_benchmark:
                missing.append(dataset)
    
    return missing


def main():
    """Main analysis."""
    print("Analyzing benchmark datasets...")
    
    # Load datasets
    datasets = load_datasets()
    print(f"Total benchmark datasets: {len(datasets)}")
    
    # Analyze categories
    categories = analyze_categories(datasets)
    print("\nBenchmark categories found:")
    for category, count in categories.most_common():
        print(f"  {category}: {count}")
    
    # Existing sources (from builder.py SOURCE_BASE_WEIGHTS)
    existing_sources = [
        'lmsys', 'arena', 'livebench', 'gsm8k', 'arc', 'bbh', 'agieval',
        'mathvista', 'frontiermath', 'aime', 'stateval', 'gpqa',
        'bigcodebench', 'humaneval', 'swebench', 'aider', 'livecodebench',
        'scicode', 'tool_use', 'mmlu', 'mmlu_pro', 'mixeval_x', 'chinese',
        'ailuminate', 'megabench', 'helm', 'domain_specific', 'vision',
        'math', 'hellaswag', 'truthfulqa', 'multilingual', 'safety'
    ]
    
    # Identify missing benchmarks
    missing = identify_missing_benchmarks(datasets, existing_sources)
    print(f"\nMissing benchmark datasets (not in existing sources): {len(missing)}")
    
    # Show top missing benchmarks
    print("\nTop 20 missing benchmark datasets:")
    for i, dataset in enumerate(missing[:20]):
        print(f"{i+1:2d}. {dataset['id']}")
        print(f"     Score: {dataset.get('benchmark_score', 0)}, "
              f"Downloads: {dataset.get('downloads', 0):,}")
        
        # Show why it's missing (category hints)
        dataset_id = dataset['id'].lower()
        description = dataset.get('description', '').lower()
        
        # Detect category
        categories_detected = []
        if any(word in dataset_id for word in ['math', 'algebra', 'calculus']):
            categories_detected.append('math')
        if any(word in dataset_id for word in ['code', 'programming', 'software']):
            categories_detected.append('coding')
        if any(word in dataset_id for word in ['reasoning', 'logic']):
            categories_detected.append('reasoning')
        if any(word in dataset_id for word in ['qa', 'question', 'answer']):
            categories_detected.append('qa')
        if any(word in dataset_id for word in ['vision', 'image', 'video', 'visual']):
            categories_detected.append('vision')
        if any(word in dataset_id for word in ['safety', 'alignment', 'toxicity']):
            categories_detected.append('safety')
        if any(word in dataset_id for word in ['medical', 'health', 'biology']):
            categories_detected.append('medical')
        
        if categories_detected:
            print(f"     Categories: {', '.join(categories_detected)}")
        
        # Short description
        desc = dataset.get('description', '')[:100]
        if len(desc) > 100:
            desc = desc[:97] + "..."
        if desc.strip():
            print(f"     {desc}")
        print()
    
    # Save missing benchmarks
    with open('/app/provider/research/missing_benchmarks.json', 'w') as f:
        json.dump(missing[:100], f, indent=2, default=str)
    
    print(f"\nMissing benchmarks saved to: /app/provider/research/missing_benchmarks.json")
    print(f"Analysis complete!")


if __name__ == "__main__":
    main()