# Research & Implementation Guide for Benchmark Data Sources

## Current Status

### ✅ Complete (Ready for Production)
- **OpenRouter API**: Fully implemented. Tested with real API response (337 models). Handles all fields including pricing, modalities, capabilities, timestamps.

- **Model Mapper**: Comprehensive mapping system with pattern matching and 100+ known aliases. Located in `router/provider_db/model_mapper.py`.

### 🚧 Implemented But Needs Testing
- **Arena.ai**: Multi-strategy scraper (Next.js data, HTML table, JS fallback). Needs real-world testing to verify parsing logic.

### ❌ Stubs (Need Dataset Schema Discovery)
- **SWE-bench**: Basic structure, but column names unknown. Needs `research_datasets.py` script to be run.
- **LiveCodeBench**: Same as above.
- **EvalPlus**: Same as above.
- **CRUXEval**: Same as above.

## How to Discover Dataset Structures

Run the research script after installing dependencies:

```bash
pip install datasets
python research_datasets.py
```

This will:
- Download each dataset (first run may take several minutes)
- Print the schema (column names, data types)
- Show example rows
- Save the information needed to adjust fetchers

## What to Look For

When inspecting dataset output, note:
1. **Model identifier column**: What field contains the model name? (e.g., "model", "model_name", "name")
2. **Score columns**: Which columns contain the benchmark scores?
3. **Score format**: Percentage (0-100) or decimal (0-1)?
4. **Splits**: Which split should we use? (test, validation, lite, etc.)
5. **Category breakdowns**: Are there separate scores for different categories? (e.g., generation, execution, repair)

## Expected Adjustments

Based on known information, here's what we expect:

| Dataset | Model Column | Score Columns | Format | Adjustment Needed |
|---------|-------------|---------------|--------|-------------------|
| SWE-bench | `model` | `resolved` or `pass@1` | % or decimal | Verify column names |
| LiveCodeBench | `model` | `pass@1` for categories: generation, repair, execution, testgen | % | Map categories to our names |
| EvalPlus | `model` | `humaneval_plus`, `mbpp_plus` | % | Confirm column names |
| CRUXEval | `model` | `crux_i`, `crux_o` | % | Verify |

## Model Mapping Integration

Once we know the model names used in each dataset, the `model_mapper.to_canonical()` function will convert them to OpenRouter IDs. You may need to extend `model_mapper.py` with additional alias entries based on the actual model names encountered.

## Testing Strategy

1. Run each fetcher individually and print output:
```python
import asyncio
from router.provider_db.sources import fetch_swe_bench

records = asyncio.run(fetch_swe_bench())
print(f"Got {len(records)} records")
if records:
    print(f"Example: {records[0]}")
```

2. Check that all `model_id` fields are being converted to canonical OpenRouter format.
3. Verify no errors and reasonable number of records (expect 10-100 models depending on dataset).

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Run research script**: `python research_datasets.py`
3. **Update fetchers**: Adjust column names and score extraction based on findings
4. **Expand model_mapper**: Add aliases for any model names that don't match existing patterns
5. **Test end-to-end**: Run `python -m router.provider_db build -o test.db` and verify database content

## Notes

- HF datasets are large (~1GB each). Use `load_dataset(..., split='test')` to limit.
- Some datasets may have multiple splits (e.g., swebench.lite vs swebench.full). Choose appropriate.
- Consider using dataset caching: `load_dataset(..., cache_dir="./hf_cache")`
