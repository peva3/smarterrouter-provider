# Provider Database Builder

**Builds `provider.db` - a SQLite database containing benchmark scores that seamlessly integrate with SmarterRouter's existing RouterEngine.**

## What This Does

This pipeline fetches benchmark data from multiple sources and creates a `provider.db` that SmarterRouter can use for intelligent model routing WITHOUT requiring expensive per-model local profiling.

## Data Sources

The system pulls from 13 benchmark sources for maximum data coverage:

### Primary Sources (API/HuggingFace)

| Score Field | Source | Description | Scale |
|-------------|--------|-------------|-------|
| `elo_rating` | **LMSYS Chatbot Arena** | Human preference ELO ratings from pairwise comparisons | 1000+ (raw) |
| `elo_rating` | **Arena.ai** | ELO ratings for text, coding, and vision | 1000+ (raw) |
| `reasoning_score` | **LiveBench** | Reasoning on never-before-seen problems (no contamination) | 0-100 |
| `coding_score` | **BigCodeBench** | Realistic coding tasks requiring multi-file reasoning | 0-100 |
| `coding_score` | **SWE-bench** | Real software engineering issues from GitHub | 0-100 |
| `coding_score` | **Aider** | Polyglot code editing and refactoring benchmark | 0-100 |
| `general_score` | **MMLU** | 57 subjects from STEM to social sciences | 0-100 |

### Additional Sources (Fallback Data)

| Score Field | Source | Description | Scale |
|-------------|--------|-------------|-------|
| `reasoning_score` | **GSM8K** | Grade-school math problems requiring multi-step reasoning | 0-100 |
| `reasoning_score` | **ARC** | Grade-school science questions (AI2 Reasoning Challenge) | 0-100 |
| `reasoning_score` | **BBH** | Big-Bench Hard - 23 challenging multi-step reasoning tasks | 0-100 |
| `reasoning_score` | **MathVista** | Mathematical reasoning in visual contexts | 0-100 |
| `reasoning_score` | **AGIEval** | Human-centric reasoning (Gaokao, SAT, LSAT, etc.) | 0-100 |
| `coding_score` | **HumanEval** | 164 Python programming problems with unit tests | 0-100 |
| `general_score` | **MMLU-Pro** | Harder MMLU with 10 choices instead of 4 | 0-100 |

### Data Source Details

#### LMSYS Chatbot Arena
- **Purpose**: Overall capability ranking via human preference
- **Method**: ~1M+ pairwise comparisons, ELO rating
- **URL**: `https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard`
- **Score Range**: 1000-1400+ (higher is better)
- **Router Normalization**: `(elo - 1000) / 800` → 0.0-1.5 scale

#### LiveBench
- **Purpose**: Measure reasoning on fresh, uncontaminated problems
- **Method**: Continuously updated with new problems not in training data
- **URL**: `https://livebench.ai`
- **Categories**: Coding, Math, Reasoning
- **Score Range**: 0-100 (percentage correct)

#### BigCodeBench
- **Purpose**: Realistic coding capability assessment
- **Method**: Complex programming tasks requiring multi-file reasoning
- **URL**: `https://huggingface.co/datasets/bigcode/bigcodebench`
- **Score Range**: 0-100 (pass rate)

#### MMLU (Massive Multitask Language Understanding)
- **Purpose**: Broad knowledge and problem-solving
- **Method**: 57 subjects, 15,908 multiple-choice questions
- **URL**: `https://huggingface.co/datasets/cais/mmlu`
- **Score Range**: 0-100 (accuracy)

#### MMLU-Pro
- **Purpose**: More challenging version of MMLU
- **Method**: 12K questions, 10 choices (vs 4), more reasoning-focused
- **URL**: `https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro`
- **Score Range**: 0-100 (accuracy)
- **Leaderboard**: Claude-3.5-Sonnet: 76%, GPT-4o: 72%

#### GSM8K (Grade School Math 8K)
- **Purpose**: Multi-step mathematical reasoning
- **Method**: 8.5K grade-school math word problems, 2-8 steps
- **URL**: `https://huggingface.co/datasets/openai/gsm8k`
- **Score Range**: 0-100 (pass rate)
- **Leaderboard**: GPT-4o: 89.5%, Claude-3.5-Sonnet: 86%

#### HumanEval
- **Purpose**: Code generation capability
- **Method**: 164 Python problems with function signatures, docstrings, tests
- **URL**: `https://huggingface.co/datasets/openai/humaneval`
- **Score Range**: 0-100 (pass@1)
- **Leaderboard**: Claude-3.5-Sonnet: 92%, GPT-4o: 90%

#### SWE-bench
- **Purpose**: Software engineering capability on real GitHub issues
- **Method**: Models must generate patches that resolve actual GitHub issues and pass tests
- **URL**: `https://www.swebench.com`
- **Score Range**: 0-100 (percentage resolved)
- **Leaderboard**: Claude 4.6 Opus: 85.2% (Verified)

#### Aider
- **Purpose**: Code editing and refactoring capability
- **Method**: Polyglot benchmark of 225 coding exercises across multiple languages
- **URL**: `https://aider.chat/docs/leaderboards/`
- **Score Range**: 0-100 (percentage correct)
- **Leaderboard**: GPT-5 (high): 88.0%

#### MathVista
- **Purpose**: Mathematical reasoning in visual contexts
- **Method**: Benchmark derived from multimodal datasets involving mathematics and newly created datasets
- **URL**: `https://mathvista.github.io/`
- **Score Range**: 0-100 (overall accuracy)
- **Leaderboard**: InternVL2-Pro: 65.8%

#### AGIEval
- **Purpose**: Human-centric benchmark specifically designed to evaluate general abilities in tasks pertinent to human cognition and problem-solving
- **Method**: 20 official, public, and high-standard admission and qualification exams
- **URL**: `https://github.com/ruixiangcui/AGIEval`
- **Score Range**: 0-100 (average accuracy)
- **Leaderboard**: GPT-4o: 71.4%

#### ARC (AI2 Reasoning Challenge)
- **Purpose**: Science reasoning and general knowledge
- **Method**: 7.7K grade-school science questions (Challenge + Easy)
- **URL**: `https://huggingface.co/datasets/allenai/ai2_arc`
- **Score Range**: 0-100 (accuracy)

#### BBH (Big-Bench Hard)
- **Purpose**: Complex multi-step reasoning
- **Method**: 23 challenging tasks (boolean expressions, logical deduction, etc.)
- **URL**: `https://huggingface.co/datasets/lukaemon/bbh`
- **Score Range**: 0-100 (accuracy)
- **Leaderboard**: GPT-4o: 72%, Claude-3.5-Sonnet: 70%

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build database
python -m router.provider_db build -o data/provider.db

# With verbose logging
python -m router.provider_db build -o data/provider.db -v
```

## Database Schema

```sql
CREATE TABLE model_benchmarks (
    model_id TEXT PRIMARY KEY,
    reasoning_score REAL NOT NULL DEFAULT 0.0,  -- 0-100
    coding_score REAL NOT NULL DEFAULT 0.0,      -- 0-100
    general_score REAL NOT NULL DEFAULT 0.0,    -- 0-100
    elo_rating INTEGER NOT NULL DEFAULT 1000,  -- 1000+
    last_updated TIMESTAMP
);

CREATE TABLE aliases (
    alias TEXT PRIMARY KEY,
    canonical_id TEXT,
    confidence REAL DEFAULT 1.0
);
```

## Router Integration

SmarterRouter queries the database like this:

```python
# RouterEngine calls this:
benchmarks = provider_db.get_benchmarks_for_models([model_id_1, model_id_2, ...])
# Returns: {model_id: {reasoning_score, coding_score, general_score, elo_rating}}
```

## Scoring Formula (in Router)

The router applies this formula for each category:

```
Combined = (benchmark × 1.5 × Q) + (elo × 1.0 × Q) + (profile × 0.8 × Q) + (inference × 0.4 × Q)
```

Where Q = user quality preference + 0.5

### Normalization

- If benchmark > 1: router divides by 100 (assumes 0-100 scale)
- If elo > 200: normalizes as `max(min((elo - 1000) / 800, 1.5), 0.0)`

## Capability Detection

**IMPORTANT**: The router IGNORES database capability fields. Instead, it uses hardcoded keyword matching on model names:

- **Vision**: `llava`, `pixtral`, `vision`, `gpt-4o`, `claude-3`, `gemini`, `minicpm`, `moondream`
- **Tools**: `gpt-4`, `claude-3`, `mistral-large`, `qwen2.5`, `llama3.1`, `command-r`, `hermes`

The builder automatically generates aliases with these keywords when appropriate.

## Docker

Build the Docker image:

```bash
docker build -t provider-db-builder:latest .
```

Run the builder to generate `provider.db`:

```bash
# Create data directory
mkdir -p data

# Run the build (outputs to data/provider.db)
docker run --rm \
  -v $(pwd)/data:/app/data \
  provider-db-builder:latest
```

### Docker with Custom OpenRouter API Key

If you have an OpenRouter API key for higher rate limits:

```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  -e OPENROUTER_API_KEY=your-key-here \
  provider-db-builder:latest
```

### Using the Database

After the build completes, `data/provider.db` will contain the latest benchmark data. You can:

1. **Copy to SmarterRouter**: Place the file in SmarterRouter's data directory
2. **Inspect**: `python -m router.provider_db.cli inspect openai/gpt-4 --db-path data/provider.db`
3. **Validate**: `python -m router.provider_db.cli validate --db-path data/provider.db`
4. **Check health**: `python -m router.provider_db.cli health --db-path data/provider.db`

## Automation with Crontab

Schedule the build to run twice daily (10am and 10pm EST) and optionally commit to GitHub:

```bash
# Edit crontab
crontab -e
```

Add these lines (adjust paths as needed):

```crontab
# Build provider.db at 10:00 AM EST (15:00 UTC)
0 15 * * * cd /path/to/provider && docker run --rm -v $(pwd)/data:/app/data provider-db-builder:latest

# Build provider.db at 10:00 PM EST (03:00 UTC)
0 3 * * * cd /path/to/provider && docker run --rm -v $(pwd)/data:/app/data provider-db-builder:latest

# Optional: Push to GitHub at midnight EST (05:00 UTC)
0 5 * * * cd /path/to/provider && git add data/provider.db data/provider.db.sha256 && git diff --cached --quiet || git commit -m "Update provider.db ($(date +\%Y-\%m-\%d))" && git push origin main
```

See `CRONTAB_EXAMPLE.txt` for a detailed example with logging and notes.

---

## Files

```
router/provider_db/
  __init__.py
  models.py           # Pydantic schemas
  database.py         # SQLite operations
  model_mapper.py     # Name → canonical ID mapping
  builder.py          # Orchestration
  cli.py              # CLI entry point
  sources/
    __init__.py
    openrouter.py     # Model catalog
    lmsys_arena.py    # ELO ratings
    livebench.py      # Reasoning scores
    bigcodebench.py   # Coding scores
    mmlu.py           # General knowledge (MMLU)
    mmlu_pro.py       # General knowledge (MMLU-Pro)
    gsm8k.py          # Math reasoning (GSM8K)
    humaneval.py      # Coding (HumanEval)
    swebench.py       # Coding (SWE-bench)
    aider.py          # Coding (Aider)
    arc.py            # Science reasoning (ARC)
    bbh.py            # Complex reasoning (BBH)
    mathvista.py      # Math reasoning (MathVista)
    agieval.py        # General reasoning (AGIEval)
    arena.py          # ELO ratings (Arena.ai)
    eqbench.py        # Creative writing
```

## Testing

```bash
# Run unit tests
pytest tests/

# Quick validation
python -c "
from router.provider_db.database import ProviderDB
db = ProviderDB('data/provider.db')
stats = db.get_stats()
print(f'Models: {stats[\"total_models\"]}')
print(f'Aliases: {stats[\"total_aliases\"]}')
"
```

## SmarterRouter Compatibility

This database is fully compatible with **SmarterRouter's RouterEngine**. 

### Schema Verification

| SmarterRouter Expects | Our Implementation |
|---------------------|-------------------|
| `model_id` (TEXT PRIMARY KEY) | ✅ TEXT PRIMARY KEY |
| `reasoning_score` (REAL, 0-100) | ✅ REAL, 0-100 |
| `coding_score` (REAL, 0-100) | ✅ REAL, 0-100 |
| `general_score` (REAL, 0-100) | ✅ REAL, 0-100 |
| `elo_rating` (INTEGER, 1000+) | ✅ INTEGER, 1000+ |

### Coverage Statistics

- **Total Models**: 436 (100% of OpenRouter catalog)
- **With Real Benchmark Data**: 324 (74.3%)
- **With Heuristic Estimates**: 112 (25.7%)
- **ELO Range**: 1010-1505
- **Score Ranges**: All 0-100 scale

### Features Implemented

- ✅ **Archive System** - Never delete models, preserve historical data
- ✅ **Incremental Updates** - Only updates changed models
- ✅ **Auto-Archive** - Marks removed OpenRouter models as archived
- ✅ **Twice Daily Sync** - GitHub Actions at 10am/10pm EST
- ✅ **100% Coverage** - All OpenRouter models have benchmark data

### Running with SmarterRouter

```bash
# Build the database
python -m router.provider_db.cli build --db-path data/provider.db

# Copy to SmarterRouter data directory
cp data/provider.db /path/to/smarterrouter/data/provider.db
```

## Requirements

- Python 3.11+
- aiohttp
- datasets (for HF benchmarks)
- pydantic

## Notes

- Scores default to 0 (or 1000 for ELO) if not found in benchmarks
- The builder auto-generates aliases including vision/tool keywords for capability detection
- Database is ~1-2 MB for 337+ models
- Run weekly to keep benchmarks fresh
- **Graceful Degradation**: If multiple sources fail, the system continues with available data. Each source is fetched independently with retry logic.

### Score Aggregation

When multiple sources provide scores for the same category (e.g., both MMLU and MMLU-Pro provide general scores), the builder averages them:

```
final_score = (score1 + score2 + ...) / count
```

This provides more robust estimates and handles missing data gracefully.
