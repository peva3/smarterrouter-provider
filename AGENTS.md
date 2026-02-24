# PROVIDERS-AGENTS.md - External Provider System

**Purpose**: Technical context for building provider.db that perfectly integrates with SmarterRouter's RouterEngine.

**CRITICAL UPDATE**: The RouterEngine expects a specific schema and scoring format. This document supersedes earlier design assumptions.

---

## ACTUAL RouterEngine Requirements (from source analysis)

### Database Schema (SQLite)

The router queries `provider.db` via `get_benchmarks_for_models()` and expects:

```sql
CREATE TABLE IF NOT EXISTS model_benchmarks (
    model_id TEXT PRIMARY KEY,
    reasoning_score REAL,   -- Scale: 0-100 (higher is better)
    coding_score REAL,      -- Scale: 0-100
    general_score REAL,     -- Scale: 0-100 (maps to 'Factual' in router)
    elo_rating INTEGER      -- Scale: 1000+ (standard ELO)
);
```

**NOTICE**: The old `benchmarks` table with multiple rows per model is WRONG. Use a single-row-per-model table with these 4 pre-aggregated scores.

---

## Data Sources & Mapping

The router's scoring formula expects these specific benchmark sources:

- **reasoning_score**: LiveBench (not Arena reasoning, not CRUXEval)
- **coding_score**: BigCodeBench (not SWE-bench + LCB + EvalPlus)
- **general_score**: MMLU (not Arena overall)
- **elo_rating**: LMSYS Chatbot Arena (not arena.ai)
- **Chinese-specific benchmarks**: Chinese reasoning (C-MATH), Chinese coding (Chinese programming evaluation), Chinese ELO estimation (for models not in LMSYS)

**Correction**: The earlier design used Arena.ai as an Elo source. The actual router expects **LMSYS Chatbot Arena** ELO ratings.

---

## Scoring Formula (Understanding the Router)

For each category (Reasoning, Coding, Factual/General), the router calculates:

```
Combined Category Score = (B × 1.5 × Q) + (E × 1.0 × Q) + (P × 0.8 × Q) + (I × 0.4 × Q)
```

Where:
- **B** = Benchmark score from provider.db (0-100)
- **E** = ELO signal (normalized from 1000+)
- **P** = Profile score from local profiler (0.0-1.0)
- **I** = Inference score from name-based heuristic (0.0-1.0)
- **Q** = Quality weight from user config (`pref + 0.5`)

**ELO Normalization** (applied by router):
```python
if elo_rating > 200:
    normalized_elo = max(min((elo_rating - 1000) / 800, 1.5), 0.0)
else:
    normalized_elo = 0.0
```

**Missing data**: If any score is missing (NULL/None), router uses 0.0 for that component.

---

## "Dominant Category" Multiplier

If prompt analysis identifies a dominant category (weight > 0.5) AND the model has a valid score for that category (> 0.15), apply **20× multiplier** to the final model selection score. This prioritizes task-specialized models.

---

## Capability Detection (HARDCODED - Cannot Be Set in DB)

The router **IGNORES** `supports_vision` and `supports_tools` booleans from the database. Instead, it does strict keyword matching on the model's `name` field:

**Vision Keywords** (any match → vision capable):
- `llava`, `pixtral`, `vision`, `gpt-4o`, `claude-3`, `gemini`, `minicpm`, `moondream`

**Tool Keywords** (any match → tool calling capable):
- `gpt-4`, `claude-3`, `mistral-large`, `qwen2.5`, `llama3.1`, `command-r`, `hermes`

**Action**: Ensure model names in the database (or aliases) contain these keywords if the model supports those capabilities.

---

## Practical Implementation Guide

### 1. Fetcher Data Sources (CORRECTED)

| Source | What to Extract | Categories | Notes |
|--------|----------------|------------|-------|
| **OpenRouter API** | Model catalog + pricing + context lengths | N/A | Use for model list, NOT for benchmark scores |
| **LMSYS Chatbot Arena** | Elo ratings | Overall Elo | This is the `elo_rating` field |
| **LiveBench** | Reasoning benchmarks | `reasoning_score` | Convert to 0-100 |
| **BigCodeBench** | Coding benchmarks | `coding_score` | Convert to 0-100 |
| **MMLU** | General knowledge | `general_score` | Convert to 0-100 |
| *(Optional)* SWE-bench, EvalPlus, CRUXEval | **Not used** | - | Router doesn't use these |

### 2. Table Structure (FINAL)

```sql
CREATE TABLE model_benchmarks (
    model_id TEXT PRIMARY KEY,
    reasoning_score REAL,   -- 0-100, from LiveBench
    coding_score REAL,      -- 0-100, from BigCodeBench
    general_score REAL,     -- 0-100, from MMLU
    elo_rating INTEGER      -- 1000+, from LMSYS Arena
);
-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_model_benchmarks_id ON model_benchmarks(model_id);
```

### 3. Data Flow

1. **Fetch model list** from OpenRouter → get canonical IDs (`provider/model-id`)
2. **Fetch benchmarks** from each source (LMSYS, LiveBench, BigCodeBench, MMLU)
3. **Map model names** from each source to OpenRouter canonical IDs using `model_mapper`
4. **Aggregate** per-model: For each canonical ID, compute the 4 scores (handle missing by setting 0)
5. **Insert** one row per model into `model_benchmarks`
6. **Generate aliases** for common name variations (ensure vision/tool keywords present)

### 4. Score Aggregation Logic

For each model that appears in multiple benchmark datasets:

```python
scores = {
    'reasoning': [],  # from LiveBench
    'coding': [],     # from BigCodeBench
    'general': [],    # from MMLU
}

# Collect all scores from that source
# Take average if multiple entries exist
# If no data from that source, score = 0.0
```

**Important**: Scores should be on 0-100 scale. If source provides percentage (85.5%), keep as 85.5. If source provides 0-1, multiply by 100.

### 5. ELO Handling

- LMSYS Arena provides raw ELO (typically 1000-1400 for top models)
- Router applies: `normalized_elo = max(min((elo - 1000) / 800, 1.5), 0.0)`
- Store raw ELO in database. Router normalizes.
- If ELO not available from LMSYS, try arena.ai as fallback? (confirm with smarterrouter)

---

## Changes from Original Design

We are **deviating** from the original PROVIDERS.md and AGENTS.md:

1. **Benchmark sources changed**:
   - ❌ Removed: Arena.ai (for category Elo), SWE-bench, EvalPlus, CRUXEval
   - ✅ Added: LMSYS Chatbot Arena, LiveBench, BigCodeBench, MMLU
   
2. **Schema simplified**:
   - ❌ Removed: `benchmarks` table with many rows per model
   - ✅ Added: `model_benchmarks` single row with 4 pre-aggregated scores

3. **Composite calculation moved**:
   - ❌ Our normalizer calculated composite (40% coding, 30% reasoning, 30% general)
   - ✅ Router does its own weighted combination using B/E/P/I terms
   - ✅ Our job: provide raw benchmark scores (0-100) per category

4. **Capabilities removed**:
   - ❌ Don't set `supports_vision` or `supports_tools` booleans
   - ✅ Rely on keyword matching in model name

---

## Testing Checklist

- [ ] Database has `model_benchmarks` table (not `benchmarks`)
- [ ] Each model has exactly one row (or zero if no benchmarks)
- [ ] Scores are 0-100 (not 0-1)
- [ ] ELO is integer 1000+ (not normalized)
- [ ] Missing scores are NULL or 0 (router handles both)
- [ ] Model names in `models` table or `aliases` contain vision/tool keywords
- [ ] Canonical IDs follow `provider/model-id` format
- [ ] Query `SELECT * FROM model_benchmarks WHERE model_id = ?` returns expected structure

---

## Quick Reference: What to Build

1. **Data pipeline**:
   - OpenRouter API → model catalog
   - LMSYS Arena → ELO (map model names)
   - LiveBench → Reasoning score
   - BigCodeBench → Coding score
   - MMLU → General score

2. **Database schema**: Single table `model_benchmarks` with 4 REAL/INTEGER columns

3. **Model mapping**: Convert all source model names to OpenRouter canonical IDs

4. **Name keywords**: Ensure model names/aliases include vision/tool keywords for specialized routing

5. **Output**: `provider.db` file ready for SmarterRouter consumption

---

**Last Updated**: 2025-02-23 (Corrected based on RouterEngine source analysis)
**Status**: ACTIVE - This is the correct specification

