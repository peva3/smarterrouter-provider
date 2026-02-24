#!/usr/bin/env python3
"""
Research script to discover dataset structures from HuggingFace.
Run this after installing dependencies to understand the exact format of each dataset.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from datasets import load_dataset
except ImportError:
    print("Error: datasets library not installed. Run: pip install datasets")
    sys.exit(1)


def explore_dataset(dataset_name: str, split: str = "test", max_samples: int = 3):
    """
    Load a dataset and print its structure.
    
    Args:
        dataset_name: HuggingFace dataset name (e.g., "swe-bench/benchmark")
        split: Dataset split to load (test, train, validation)
        max_samples: Number of examples to show
    """
    print(f"\n{'='*60}")
    print(f"Exploring: {dataset_name} (split={split})")
    print('='*60)
    
    try:
        dataset = load_dataset(dataset_name, split=split, trust_remote_code=True)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None
    
    print(f"Total samples: {len(dataset)}")
    print(f"Features: {dataset.features}")
    print(f"\nColumn names: {list(dataset.column_names)}")
    
    if len(dataset) > 0:
        print(f"\nFirst {min(max_samples, len(dataset))} samples:")
        for i in range(min(max_samples, len(dataset))):
            example = dataset[i]
            print(f"\n--- Sample {i+1} ---")
            for key, value in example.items():
                if isinstance(value, (str, int, float, bool, list, dict)):
                    if isinstance(value, dict):
                        print(f"  {key}: (dict with keys: {list(value.keys())})")
                    elif isinstance(value, list) and len(value) > 3:
                        print(f"  {key}: (list of {len(value)} items)")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: ({type(value).__name__})")
    
    return dataset


def main():
    """Explore all benchmark datasets."""
    datasets_to_explore = [
        ("swe-bench/benchmark", "swebench.lite"),
        ("livecodebench/benchmark", "test"),
        ("EvalPlus/evalplus", "test"),
        ("cruxeval-org/cruxeval", "test"),
    ]
    
    print("Dataset Structure Explorer")
    print("This will download datasets on first run (may take time).")
    
    for ds_name, split in datasets_to_explore:
        try:
            explore_dataset(ds_name, split)
        except Exception as e:
            print(f"\nFailed to explore {ds_name}: {e}")
    
    print("\n" + "="*60)
    print("Exploration complete!")
    print("Use this information to update the fetcher implementations.")
    print("="*60)


if __name__ == "__main__":
    main()
