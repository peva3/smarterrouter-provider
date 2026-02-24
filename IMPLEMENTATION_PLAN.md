# IMPLEMENTATION PLAN - Corrected for RouterEngine

## Database Schema (FINAL)

```sql
CREATE TABLE model_benchmarks (
    model_id TEXT PRIMARY KEY,
    reasoning_score REAL NOT NULL DEFAULT 0.0,  -- 0-100 from LiveBench
    coding_score REAL NOT NULL DEFAULT 0.0,     -- 0-100 from BigCodeBench
    general_score REAL NOT NULL DEFAULT 0.0,    -- 0-100 from MMLU
    elo_rating INTEGER NOT NULL DEFAULT 1000,  -- Raw ELO from LMSYS Arena
    last_updated TIMESTAMP NOT NULL
);

CREATE TABLE aliases (
    alias TEXT PRIMARY KEY,
    canonical_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE model_info (  -- Optional, for UI
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    context_length INTEGER,
    description TEXT,
    -- pricing optional
    FOREIGN KEY (id) REFERENCES model_benchmarks(model_id)
);

CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
```

## Data Sources (WHAT TO EXTRACT)

### 1. OpenRouter API: `/api/v1/models`
**Purpose**: Get canonical model list and IDs
**Returns**: 337 models with `id` format `provider/model-id`
**Do NOT use for benchmarks** - only to get the master list of model IDs

### 2. LiveBench: Reasoning Score
**Source**: LiveBench API or dataset
**What to get**: model name → reasoning_score (0-100)
**Map**: Convert model name to OpenRouter canonical ID via `model_mapper`
**Store in**: `model_benchmarks.reasoning_score`

### 3. BigCodeBench: Coding Score
**Source**: HuggingFace dataset or leaderboard
**What to get**: model name → coding_score (0-100)
**Map**: Via `model_mapper`
**Store in**: `model_benchmarks.coding_score`

### 4. MMLU: General Score
**Source**: HuggingFace MMLU results
**What to get**: model name → general_score (0-100)
**Map**: Via `model_mapper`
**Store in**: `model_benchmarks.general_score`

### 5. LMSYS Chatbot Arena: ELO
**Source**: LMSYS Arena API or CSV export
**What to get**: model name → elo_rating (raw integer, typically 1000-1400)
**Map**: Via `model_mapper`
**Store in**: `model_benchmarks.elo_rating`

## Aggregation Logic

For each source, we get a dict: `{model_id: score}`

```python
# Initialize empty benchmarks for all OpenRouter models
all_models = fetch_openrouter_models()  # gives list of model IDs
benchmarks = {model_id: {} for model_id in all_models}

# Merge each source
livebench_scores = await fetch_livebench()    # → reasoning_score
bigcode_scores = await fetch_bigcodebench()  # → coding_score
mmlu_scores = await fetch_mmlu()             # → general_score
lmsys_scores = await fetch_lmsys_arena()     # → elo_rating

for model_id, score in livebench_scores.items():
    if model_id in benchmarks:
        benchmarks[model_id]['reasoning_score'] = score

for model_id, score in bigcode_scores.items():
    if model_id in benchmarks:
        benchmarks[model_id]['coding_score'] = score

# ... similarly for others

# Convert to ModelBenchmark objects, filling missing with 0 (scores) or 1000 (elo)
model_benchmarks = []
for model_id, scores in benchmarks.items():
    benchmark = ModelBenchmark(
        model_id=model_id,
        reasoning_score=scores.get('reasoning_score', 0.0),
        coding_score=scores.get('coding_score', 0.0),
        general_score=scores.get('general_score', 0.0),
        elo_rating=scores.get('elo_rating', 1000)
    )
    model_benchmarks.append(benchmark)
```

## Model Mapper Requirements

**Expand** `model_mapper.py` to handle names from:
- LiveBench: likely names like "gpt-4", "claude-3-opus", "llama-3.1-70b"
- BigCodeBench: similar
- MMLU: similar
- LMSYS: similar

Must map to OpenRouter canonical IDs like:
- `openai/gpt-4-turbo-preview`
- `anthropic/claude-3-opus-20240229`
- `meta-llama/llama-3.1-70b-instruct`

Add lots of aliases!

## What to Do NOW

1. **Research livebench.ai API** - find endpoint for leaderboard scores
2. **Research BigCodeBench** - HuggingFace or website, get coding scores
3. **Research MMLU** - find aggregated results (likely from HuggingFace or papers)
4. **Research LMSYS Arena** - find API or CSV download for Elo ratings
5. **Research model name formats** from each source to populate `model_mapper`

Then implement each fetcher to return the dict[model_id, score].

## Simplified Fetcher Interface

All fetchers should be async and return:

```python
async def fetch_<source>() -> Dict[str, Dict[str, float]]:
    """
    Returns:
        {
            "openai/gpt-4-turbo": {
                "reasoning_score": 85.5,  # or "coding_score", etc.
                "elo_rating": 1280
            },
            ...
        }
    """
```

But better: each fetcher returns scores for ONE field only. Simpler.

## Files to Create/Update

1. `sources/livebench.py` - fetch LiveBench reasoning scores
2. `sources/bigcodebench.py` - fetch coding scores
3. `sources/mmlu.py` - fetch general knowledge scores
4. `sources/lmsys_arena.py` - fetch ELO ratings
5. `model_mapper.py` - comprehensive mapping
6. `builder.py` - aggregate into ModelBenchmark list
7. `database.py` - store model_benchmarks table

Let me implement this properly.
