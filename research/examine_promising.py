#!/usr/bin/env python3
"""
Examine promising benchmark dataset in detail.
"""

from datasets import load_dataset
import pandas as pd

def examine_math_benchmark():
    """Examine the math benchmark dataset."""
    dataset_id = "nlile/math_benchmark_test_saturation"
    
    print(f"Loading dataset: {dataset_id}")
    dataset = load_dataset(dataset_id, split='train')
    
    print(f"\nDataset size: {len(dataset)}")
    print(f"Features: {dataset.features}")
    
    # Convert to pandas for easier analysis
    df = dataset.to_pandas()
    
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # Analyze models
    print(f"\nUnique models: {df['model'].nunique()}")
    print(f"Model count distribution:")
    print(df['model'].value_counts().head(20))
    
    # Analyze accuracy scores
    print(f"\nAccuracy statistics:")
    print(f"Min: {df['accuracy'].min():.2f}")
    print(f"Max: {df['accuracy'].max():.2f}")
    print(f"Mean: {df['accuracy'].mean():.2f}")
    print(f"Std: {df['accuracy'].std():.2f}")
    
    # Check for OpenRouter model IDs
    print(f"\nSample models with highest accuracy:")
    top_models = df.sort_values('accuracy', ascending=False).head(10)
    for idx, row in top_models.iterrows():
        print(f"  {row['model']}: {row['accuracy']:.1f}% (year: {row['year']})")
    
    # Check if we can map these to OpenRouter IDs
    print(f"\nChecking model name patterns:")
    for model_name in df['model'].unique()[:20]:
        print(f"  - {model_name}")
    
    return df

def check_mapping_to_openrouter(df):
    """Check how well these model names map to OpenRouter IDs."""
    # Sample OpenRouter model IDs pattern
    openrouter_patterns = [
        'openai/', 'anthropic/', 'google/', 'meta/', 'mistralai/',
        'cohere/', 'nousresearch/', 'qwen/', 'deepseek/', 'alibaba/'
    ]
    
    print(f"\nAnalyzing model name mapping to OpenRouter patterns:")
    
    mappable = 0
    for model_name in df['model'].unique():
        model_lower = model_name.lower()
        
        # Check for common provider prefixes
        if any(pattern in model_lower for pattern in openrouter_patterns):
            mappable += 1
            print(f"  ✓ {model_name}")
        else:
            # Check for known model families
            known_families = ['gpt', 'claude', 'gemini', 'llama', 'mistral', 'qwen', 'deepseek']
            if any(family in model_lower for family in known_families):
                mappable += 1
                print(f"  ~ {model_name} (known family)")
            else:
                print(f"  ✗ {model_name}")
    
    print(f"\nMappable models: {mappable}/{df['model'].nunique()} ({mappable/df['model'].nunique()*100:.1f}%)")

if __name__ == "__main__":
    df = examine_math_benchmark()
    check_mapping_to_openrouter(df)