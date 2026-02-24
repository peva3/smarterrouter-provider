# Dynamic Authority Weighting System

## Overview

The provider.db builder uses a **hybrid consensus-weighted averaging** system to aggregate benchmark scores from 33+ sources. This system:

1. **Weight sources by reliability** using tiered base weights
2. **Penalize outliers** using consensus-based correlation multipliers
3. **Compute weighted averages** that give more influence to reliable sources

This ensures the final benchmark scores are robust, reliable, and less affected by questionable data from low-quality or biased sources.

## Why Weighted Averaging?

Simple averaging treats all benchmark sources equally, but in reality:
- Some sources are more authoritative (e.g., LiveBench vs. niche Chinese benchmarks)
- Some sources may have systemic biases or errors
- Consensus is a strong indicator of truth - sources that agree with others are likely more reliable

The dynamic system automatically detects and penalizes outliers while rewarding sources that align with consensus.

## Implementation Details

### 1. Base Weights (Tier System)

Sources are categorized into three tiers based on reliability:

#### Tier 1 (Weight: 1.0) - Primary Sources
- **lmsys**: LMSYS Chatbot Arena (ELO ratings)
- **livebench**: LiveBench (reasoning)
- **bigcodebench**: BigCodeBench (coding)
- **mmlu**: MMLU (general knowledge)

These are the primary sources specified by SmarterRouter's RouterEngine.

#### Tier 2 (Weight: 0.9) - Established Benchmarks
- **gsm8k**, **arc**, **bbh**: Well-established reasoning benchmarks
- **humaneval**, **swebench**: Established coding benchmarks
- **mmlu_pro**, **mixeval_x**: Enhanced general knowledge benchmarks

#### Tier 3 (Weight: 0.8) - Specialized Benchmarks
- All other 20+ sources covering niche domains, languages, and modalities

### 2. Consensus Multipliers

For each source, we compute its correlation with the consensus of other sources:

```python
multiplier = clamp(pearson_correlation(source_scores, mean(other_scores)), 0.5, 1.5)
```

Where:
- `pearson_correlation()` calculates linear correlation (-1 to 1)
- `clamp()` restricts multiplier to 0.5-1.5 range
- A multiplier of 1.0 means the source perfectly aligns with consensus
- < 1.0 indicates the source disagrees (penalized)
- > 1.0 indicates the source strongly agrees with consensus (rewarded)

### 3. Final Weight Calculation

```
final_weight[source] = base_weight[source] × consensus_multiplier[source]
```

### 4. Weighted Average per Model Category

For each model and category (reasoning, coding, general, elo):

```
weighted_sum = Σ(score × final_weight[source])
total_weight = Σ(final_weight[source])
final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
```

## Algorithm Steps

1. **Data Collection**: Gather scores from all 33 sources, tracking source name with each score
2. **Consensus Calculation**: Compute correlation multipliers for each source
3. **Weight Calculation**: Multiply base weight by consensus multiplier
4. **Weighted Aggregation**: Apply weights to each model's category scores
5. **Range Enforcement**: Ensure scores stay within valid ranges (0-100 for scores, 1000+ for ELO)

## Code Location

The implementation is in `/app/provider/router/provider_db/builder.py`:

- **`SOURCE_BASE_WEIGHTS`** (line ~45): Tier-based base weights
- **`_fetch_all_sources()`** (line ~248): Collects scores with source tracking
- **`_compute_consensus_weights()`** (line ~768): Computes consensus multipliers
- **`_aggregate_scores()`** (line ~829): Performs weighted averaging

## Example

Consider a model with reasoning scores from three sources:

| Source | Score | Base Weight | Consensus Multiplier | Final Weight |
|--------|-------|-------------|---------------------|--------------|
| LiveBench | 80.0 | 1.0 | 1.2 | 1.2 |
| GSM8K | 85.0 | 0.9 | 1.1 | 0.99 |
| AGIEval | 95.0 | 0.8 | 0.6 | 0.48 |

Weighted average:
```
(80.0 × 1.2) + (85.0 × 0.99) + (95.0 × 0.48)
------------------------------------------- ≈ 83.2
    1.2 + 0.99 + 0.48
```

Note how AGIEval's outlier score (95) is heavily discounted due to its low consensus multiplier (0.6).

## Benefits

1. **Self-Correcting**: Outliers automatically penalized
2. **No External APIs**: Weights computed internally from consensus
3. **Source-Level Weighting**: Avoids category-specific biases
4. **Transparent**: All weights are logged during build
5. **Sustainable**: Works long-term as new sources are added

## Testing

The weighting system is tested in `test_provider_db.py`:

- **`test_aggregate_scores_weighted_averaging()`**: Verifies weighting works correctly
- **`test_compute_consensus_weights()`**: Tests consensus multiplier calculation
- **`test_aggregate_scores_multiple_reasoning_sources_averaged()`**: Tests multi-source aggregation

All 55 tests pass with the weighting system enabled.

## Integration with SmarterRouter

The weighting system is **transparent to SmarterRouter**. The RouterEngine still receives the same 4 scores per model (reasoning, coding, general, elo). The improvement is in the quality and reliability of those scores, which leads to better model routing decisions.

## Configuration

Base weights are hardcoded in `SOURCE_BASE_WEIGHTS` based on tier assignments. To modify:

1. Edit the `SOURCE_BASE_WEIGHTS` dictionary in `builder.py`
2. Run tests to verify changes
3. Rebuild provider.db

Future enhancements could make weights configurable via external configuration.

## Future Enhancements

1. **Time-Decay Weights**: Older benchmark results could be weighted less
2. **Category-Specific Multipliers**: Some sources may be reliable in one category but not others
3. **Statistical Validation**: Compare weighted scores against ground truth when available
4. **Community Voting**: Allow users to vote on source reliability

## Conclusion

The dynamic authority weighting system significantly improves benchmark score reliability by:
- Prioritizing high-quality sources
- Penalizing outliers that disagree with consensus
- Providing robust, defensible score aggregations

This ensures SmarterRouter users get the best possible model routing based on the most reliable benchmark data available.