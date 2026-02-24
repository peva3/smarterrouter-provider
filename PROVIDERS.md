# External Provider Database - Design & Implementation Guide

## Executive Summary

SmarterRouter currently only supports local backends (Ollama, llama.cpp). This document outlines the plan to add support for remote LLM providers (OpenAI, Anthropic, Groq, Together, etc.) through a curated external benchmark database (`provider.db`) that eliminates the need for expensive per-deployment profiling.

**Key insight**: Instead of profiling each remote model (costing $0.10-0.50 per model in judge API tokens), we'll precompile benchmark data from public sources (OpenRouter API, Arena.ai, SWE-bench, etc.) into a single SQLite database that users download automatically.

**Expected capabilities**:
- Support 300+ models from 20+ providers
- Routing based on quality (benchmarks), cost, latency, and capabilities
- Automatic health monitoring and circuit breakers
- No per-call inference overhead
- One-time download ~5-10 MB

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Provider Database Schema](#provider-database-schema)
3. [Data Sources](#data-sources)
4. [Implementation Phases](#implementation-phases)
5. [Configuration](#configuration)
6. [Benchmark Normalization](#benchmark-normalization)
7. [Model Name Mapping](#model-name-mapping)
8. [Cost-Aware Routing](#cost-aware-routing)
9. [Risks & Mitigations](#risks--mitigations)
10. [FAQ](#faq)

---

## Architecture Overview

### Current State (Single Backend)

```
User Query → RouterEngine → Single Backend (e.g., Ollama) → Model Selection
     ↓
Profiling: Active (call judge prompts, measure VRAM)
Cost: ~$0.10-0.50 per model
Scale: 10-50 local models max
```

### Proposed State (Multi-Backend + Provider DB)

```
User Query → RouterEngine → BackendRegistry
                                    ├─ Local Backends (Ollama, llama.cpp)
                                    └─ Remote Backends (OpenAI, Anthropic, etc.)
                                            ↓
                               Provider Database (provider.db)
                               - Model catalog (337+ entries)
                               - Benchmark scores (Arena, SWE-bench, etc.)
                               - Pricing data
                               - Capabilities (vision, tools)
                               - Latency tracking
```

**Key components**:

1. **BackendRegistry** - Manages multiple `LLMBackend` instances, health, and failover
2. **ProviderDB** - SQLite database with precompiled benchmark data (downloaded, not profiled)
3. **Model namespacing** - `{provider}:{model-id}` format (e.g., `openai:gpt-4-turbo`)
4. **Benchmark fusion** - Combine scores from multiple sources into dimension scores

---

## Provider Database Schema

### `models` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Canonical identifier (e.g., `openai/gpt-4-turbo-preview`) |
| `name` | TEXT | Display name |
| `provider` | TEXT | Extracted from ID prefix (`openai`, `anthropic`, `google`) |
| `canonical_slug` | TEXT | Stable slug from source |
| `hugging_face_id` | TEXT | Link to HF repo if applicable |
| `context_length` | INTEGER | Max context window |
| `max_completion_tokens` | INTEGER | Provider limit |
| `is_moderated` | BOOLEAN | Whether content filtering enabled |
| `created` | DATETIME | When model was added to source |
| `expiration_date` | DATETIME NULL | If model will be retired |
| `description` | TEXT | Long description |
| `modality` | TEXT | e.g., `text+image+file->text` |
| `input_modalities` | JSON | Array |
| `output_modalities` | JSON | Array |
| `tokenizer` | TEXT | Tokenizer family |
| `supported_parameters` | JSON | API parameters supported |
| `prompt_cost` | REAL | USD per token (input) |
| `completion_cost` | REAL | USD per token (output) |
| `image_cost` | REAL | USD per image token |
| `audio_cost` | REAL | USD per audio token |
| `reasoning_cost` | REAL | USD for reasoning tokens |
| `cache_read_cost` | REAL | USD per cached token read |
| `cache_write_cost` | REAL | USD per cached token write |
| `web_search_cost` | REAL | Extra cost for web search tool |
| `supports_vision` | BOOLEAN | Derived from modalities |
| `supports_tools` | BOOLEAN | Derived from supported_parameters |
| `supports_thinking` | BOOLEAN | Pattern match on name/ID |
| `is_deprecated` | BOOLEAN | Auto-set when expiration_date passed |
| `last_updated` | DATETIME | When this record was last synced |

### `benchmarks` table

| Column | Type | Description |
|--------|------|-------------|
| `model_id` | TEXT FK → models.id | |
| `source` | TEXT | `openrouter_arena_text`, `swe_bench`, `livecodebench_gen`, `evalplus_humaneval`, etc. |
| `category` | TEXT | `overall`, `coding`, `reasoning`, `math`, `swe_resolved`, `lcb_repair`, etc. |
| `score` | REAL | **Normalized 0-1** for routing calculations |
| `raw_score` | REAL | Original value (Elo, pass@1 %, etc.) |
| `sample_size` | INTEGER | Votes, test instances (for confidence) |
| `collected_date` | DATE | When benchmark data was gathered |
| **PK** | (model_id, source, category) | |

### `aliases` table

| Column | Type | Description |
|--------|------|-------------|
| `alias` | TEXT PK | Alternate model name (e.g., `gpt-4-turbo`, `claude-3-opus-20240229`) |
| `canonical_id` | TEXT FK → models.id | The canonical OpenRouter-style ID |
| `confidence` | REAL DEFAULT 1.0 | 1.0=exact, 0.8=fuzzy heuristic |

### `metadata` table

Simple key-value store for db-level info:
```json
{
  "last_update": "2025-02-23",
  "sources": ["openrouter", "arena", "swe_bench", "lcb", "evalplus", "cruxeval"],
  "openrouter_version": "v1",
  "arena_scrape_date": "2025-02-22"
}
```

---

## Data Sources

### Primary Sources (Tier 1 - Must Have)

| Source | What It Provides | Access Method | Models Covered | Update Freq |
|--------|------------------|---------------|----------------|-------------|
| **OpenRouter API** | Catalog, pricing, context lengths, modalities, supported params | `GET https://openrouter.ai/api/v1/models` | 337 | Real-time |
| **Arena.ai** | Human preference Elo by category (Text, Code, Vision, etc.) | HTML scrape (no API) | ~60 frontier | Daily |
| **SWE-bench** | % of GitHub issues resolved (real SWE tasks) | HuggingFace dataset | ~50 | Monthly |
| **LiveCodeBench** | Code generation, repair, execution, testgen scores | HuggingFace dataset | ~30 | Quarterly |
| **EvalPlus** | HumanEval+, MBPP+ (canonical code completion) | HuggingFace dataset | ~40 | Rare |
| **CRUXEval** | Code reasoning & execution | HuggingFace dataset | ~40 | Rare |

### Secondary Sources (Tier 2 - Nice to Have)

- **TabbyML Leaderboard** - Code completion specific
- **BigCode Models Leaderboard** - BigCode models
- **NaturalCodeBench** - From THUDM
- **HumanEval.jl** - Julia variants (probably ignore)

### Not Recommended

- CrossCodeEval, ClassEval, Code Lingua, Evo-Eval, RepoBench, OOP - too niche, limited coverage, academic

---

## Benchmark Normalization Strategy

Each source reports different metrics:

| Source | Raw Metric | Normalization | Categories Extracted |
|--------|------------|---------------|---------------------|
| Arena.ai | Elo rating (1000-1600) | `(elo - min_elo) / (max_elo - min_elo)` | `overall`, `coding`, `reasoning`, `math`, `creative_writing`, `instruction_following`, `longer_query` |
| SWE-bench | % resolved (0-100) | Direct: `score = raw / 100` | `swe_resolved`, `swe_verified`, `swe_bash_only`, `swe_multimodal`, `swe_lite` |
| LiveCodeBench | Pass % | Direct: `score = raw / 100` | `lcb_generation`, `lcb_self_repair`, `lcb_execution`, `lcb_testgen` |
| EvalPlus | pass@1 % | Direct | `humaneval`, `humaneval_plus`, `mbpp`, `mbpp_plus` |
| CRUXEval | pass@1 % | Direct | `crux_i`, `crux_o` |

### Composite Dimension Scores

RouterEngine will aggregate benchmarks into three dimensions:

```python
quality_score_coding = normalize([
    swe_resolved,
    lcb_generation,
    humaneval,
    mbpp,
    crux_i,
    tabby_completion,
    arena_coding
])

quality_score_reasoning = normalize([
    arena_reasoning,
    arena_math,
    arena_expert,
    crux_o
])

quality_score_general = normalize([
    arena_overall,
    arena_instruction_following,
    arena_creative
])
```

Normalization: `(value - min_across_models) / (max_across_models)`. Min/max computed per-category at database build time and stored in `metadata` for consistency.

---

## Model Name Mapping

### Challenge

Providers use different naming:
```
OpenRouter ID:          "openai/gpt-4-turbo-preview"
OpenAI API model:       "gpt-4-turbo-preview"
Ollama:                 "llama3.1:70b-instruct-q4_K_M"
Together:               "meta-llama/Llama-3.1-70B-Instruct"
```

### Solution: Canonical IDs + Alias Table

**Canonical**: Use OpenRouter's `id` format (`provider/model-id`) as the global canonical identifier.

**Aliasing**: The `aliases` table maps alternate names to canonical IDs.

**Lookup flow in SmarterRouter**:
1. User adds backend with model name pattern (e.g., `gpt-4-turbo` via OpenAI backend)
2. `BackendRegistry.list_models()` returns `ModelInfo(name="gpt-4-turbo")`
3. `RouterEngine` needs benchmarks → query provider.db:
   ```sql
   SELECT canonical_id FROM aliases WHERE alias = 'gpt-4-turbo'
   ```
4. If found, use `canonical_id` to join benchmarks
5. If not found, try fuzzy matching:
   - Lowercase, strip separators, extract size (70b), family (llama)
   - Match against `models` table by provider+family+size
6. If still no match → fallback score (0.5) + warning log

**Admin override**: Users can manually add aliases via admin API or YAML file:
```yaml
aliases:
  - alias: "my-custom-model"
    canonical: "openai/gpt-4-turbo"
    confidence: 1.0
```

---

## Cost-Aware Routing

### Data Availability

OpenRouter provides per-token costs as strings:
```json
"pricing": {
  "prompt": "0.000002",      // $0.002 / 1k tokens
  "completion": "0.000012",  // $0.012 / 1k tokens
  "image": "0.000002",
  "web_search": "0.01"
}
```

### Cost Calculation

For a typical chat request:
```
input_tokens = 1000
output_tokens = 500
cost = (1000 * prompt_cost) + (500 * completion_cost)
```

We'll estimate per-request cost using recent average token counts from usage logs (or defaults: 1k in, 500 out).

### Routing Configuration

```bash
# .env
ROUTER_COST_OPTIMIZATION=balanced  # "quality", "balanced", "cheapest"
ROUTER_MAX_COST_PER_1K_OUTPUT=0.05  # Hard cap $0.05 / 1k output tokens
```

Scoring penalty:
```python
if cost_per_1k_output > max_allowed:
    combined_score *= 0.0  # reject
else:
    # Penalty relative to reference (GPT-4 ~$0.03/1k output)
    cost_penalty = 1.0 - (cost_per_1k_output / 0.03)
    cost_penalty = max(0, min(1, cost_penalty))
    
    if cost_mode == "cheapest":
        combined_score = 0.7 * cost_penalty + 0.3 * quality_score
    elif cost_mode == "balanced":
        combined_score = 0.5 * quality_score + 0.5 * cost_penalty
    else:  # quality
        combined_score = 0.9 * quality_score + 0.1 * cost_penalty
```

---

## Latency Tracking

### Measurement

`BackendRegistry` will run a background task every 30s:
- Send lightweight request to each backend's `/health` or `/models` endpoint
- Record round-trip time (RTT)
- Keep p50, p95, p99 rolling window (last 100 samples)

### Routing Impact

```python
latency_ms = backend_metadata.latency_p50
if latency_ms > 500:
    latency_penalty = 1.0 - ((latency_ms - 500) / 1000)
    latency_penalty = max(0.1, latency_penalty)  # floor at 0.1
    combined_score *= latency_penalty
```

---

## Circuit Breakers

### Implementation

Per-backend failure tracking:
```python
class BackendMetadata:
    health: Literal["healthy", "degraded", "unhealthy", "circuit_open"]
    failure_count: int
    last_failure: float  # timestamp
    circuit_open_until: float | None
```

On exception (timeout, 5xx, rate limit):
```python
meta.failure_count += 1
if meta.failure_count >= 5:
    meta.health = "circuit_open"
    meta.circuit_open_until = time.time() + 300  # 5 min cooldown
```

Half-open state: After cooldown, allow one test request. If succeeds → healthy; if fails → reset cooldown.

### Health Check Task

Separate background coroutine (every 60s) that:
- Calls backend `/health` or `/models` (lightweight)
- Restores `healthy` if response OK
- Logs warnings for degraded/unhealthy backends

---

## Implementation Phases

### Phase 1: Provider Database Builder (Standalone) (Week 1-2)

**Deliverable**: Script/CLI that produces `provider.db`

Components:
- `router/provider_db/` package
- `models.py` - Pydantic schemas for incoming JSON
- `sources/` - Individual fetcher modules:
  - `openrouter.py` - API fetch
  - `arena.py` - HTML scraper
  - `swe_bench.py` - HF dataset download
  - `livecodebench.py` - HF dataset
  - `evalplus.py` - HF dataset
  - `cruxeval.py` - HF dataset
- `normalizer.py` - Score normalization, alias generation
- `writer.py` - SQLite creation with schema
- `publisher.py` - Upload to GitHub releases (optional)
- `cli.py` - `python -m router.provider_db build`

**Output**: `provider.db` (SQLite, ~5-10 MB compressed)

---

### Phase 2: SmarterRouter Integration (Week 3)

**Files to modify**:

1. `router/backends/__init__.py` - Add `BackendRegistry` class to replace single `backend`
2. `router/config.py` - Add config options:
   ```python
   external_providers_enabled: bool = False
   provider_db_url: str | None = None
   provider_db_auto_update: bool = True
   provider_db_update_interval: int = 604800  # 7 days
   show_all_remote_models: bool = False
   cost_optimization_mode: str = "balanced"
   max_cost_per_1k_output: float | None = None
   ```
3. `main.py` - Init `BackendRegistry`, download provider.db on startup
4. `router/router.py` - Adapt to use registry instead of single backend
5. `router/benchmark_db.py` - Add `ProviderDB` class wrapper, alias lookup
6. `router/vram_manager.py` - Skip VRAM ops for remote backends (capability detection)

---

### Phase 3: Admin UI & Management (Week 4)

**New endpoints**:

- `GET /admin/provider-db/status` - Last update, model count, source health
- `POST /admin/provider-db/refresh` - Trigger re-download
- `GET /admin/backends` - List registered backends, health, latency, rate limits
- `POST /admin/backends/{name}/circuit-reset` - Manually reset circuit breaker
- `GET /admin/models?filter=remote` - Filter remote vs local models
- `POST /admin/aliases` - CRUD for model alias mappings

**CLI commands**:
```bash
python -m router.provider_db build --force
python -m router.provider_db serve  # Local HTTP server for custom db
python -m router.backends register --name openai --url ... --api-key ...
```

---

### Phase 4: Testing & Polish (Week 5-6)

- Unit tests for each fetcher (mock HTTP responses)
- Integration tests with fake provider.db
- Benchmark normalization unit tests
- End-to-end routing tests with mixed backends
- Performance: ensure provider.db queries are fast (<1ms) - use indexes
- Migration guide: how existing users adopt without disruption

---

## Configuration

### Environment Variables

```bash
# Enable external providers
ROUTER_EXTERNAL_PROVIDERS=true

# Provider DB location (auto-downloaded if URL provided)
PROVIDER_DB_URL=https://github.com/yourorg/provider-data/releases/download/latest/provider.db
PROVIDER_DB_PATH=/app/data/provider.db  # Optional: manual path

# Auto-update frequency (seconds)
PROUTER_DB_UPDATE_INTERVAL=604800

# Model visibility
ROUTER_SHOW_ALL_REMOTE_MODELS=false  # Default: only models with benchmarks

# Cost optimization
ROUTER_COST_OPTIMIZATION=balanced  # "quality", "balanced", "cheapest"
ROUTER_MAX_COST_PER_1K_OUTPUT=0.05  # Reject models above this

# Backend-specific configs (still needed)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

### Backend Registration

Two ways:

**1. Automatic via provider.db** (if using OpenRouter):
```bash
ROUTER_EXTERNAL_PROVIDERS=true
# Registry auto-discovers models from provider.db
# But you still need to configure API keys for each backend in main.py or via env
```

**2. Manual backend config** (for custom endpoints):
```python
# In code or environment
ROUTER_BACKENDS_JSON='[
  {
    "name": "openai",
    "type": "openai_compatible",
    "url": "https://api.openai.com/v1",
    "api_key": "...",
    "provider": "openai"
  },
  {
    "name": "groq",
    "type": "openai_compatible",
    "url": "https://api.groq.com/openai/v1",
    "api_key": "...",
    "provider": "groq"
  }
]'
```

---

## Benchmark Normalization Details

### Score Sources & Weights

| Source | Categories | Weight in Composite |
|--------|------------|---------------------|
| Arena.ai (text) | overall, coding, reasoning, math | 30% |
| SWE-bench | swe_resolved, swe_verified | 30% |
| LiveCodeBench | generation, repair, execution | 20% |
| EvalPlus | humaneval, mbpp | 10% |
| CRUXEval | crux_i, crux_o | 10% |

### Composite Calculation

```python
def calculate_quality_score(model_id: str) -> float:
    benchmarks = provider_db.get_benchmarks(model_id)
    
    # Arena-derived
    arena_coding = avg(benchmarks.get('arena_coding'), benchmarks.get('arena_overall'))
    arena_reasoning = avg(benchmarks.get('arena_reasoning'), benchmarks.get('arena_math'))
    
    # Code benchmarks
    coding_score = avg(
        benchmarks.get('swe_resolved'),
        benchmarks.get('lcb_generation'),
        benchmarks.get('humaneval'),
        benchmarks.get('mbpp'),
        arena_coding
    )
    
    reasoning_score = avg(
        arena_reasoning,
        benchmarks.get('crux_o'),
        benchmarks.get('arena_expert')
    )
    
    general_score = avg(
        benchmarks.get('arena_overall'),
        benchmarks.get('arena_instruction_following')
    )
    
    # Weighted sum
    final = (
        0.4 * coding_score +
        0.3 * reasoning_score +
        0.3 * general_score
    )
    return final
```

If any component missing, impute with category average (or fallback to 0.5).

---

## Model Name Mapping Algorithm

### Exact Matching

First try `aliases` table:
```sql
SELECT canonical_id FROM aliases WHERE alias = ?
```

### Fuzzy Matching

If exact miss, attempt heuristics:

1. **Normalize candidate**:
   ```python
   def normalize_name(name: str) -> str:
       name = name.lower()
       name = re.sub(r'[^a-z0-9]', '', name)  # Remove all separators
       return name
   ```

2. **Extract family and size**:
   ```python
   # Patterns
   patterns = {
       'gpt': r'gpt-?4(?:-turbo)?',
       'claude': r'claude-?(opus|sonnet|haiku)',
       'llama': r'llama-?3\.1.*?(\d+)b',
       'gemini': r'gemini-?(?:pro|flash)',
   }
   ```

3. **Query canonical models**:
   ```sql
   SELECT id FROM models 
   WHERE provider = ? 
     AND family = ? 
     AND ABS(size_b - candidate_size) <= 2  # Within 2B
   ```

4. **Score matches** and return best if confidence > 0.7

### Manual Override

Admin can add to `aliases` via API or YAML file:
```yaml
# custom_aliases.yaml
- alias: "gpt-4"
  canonical: "openai/gpt-4-turbo-preview"
  confidence: 1.0
- alias: "llama3-70b"
  canonical: "ollama/llama3.1:70b-instruct-q4_K_M"
  confidence: 0.9
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **OpenRouter API changes** | High | Pin to release assets; version the db; monitor with alerts |
| **Arena.ai blocks scrapers** | Medium | Cache results aggressively; respect robots.txt; use RSS if available; fallback to cached |
| **Model ID mismatches** | High | Alias table + fuzzy matching; admin UI to add mappings; logging for unknown models |
| **Stale benchmark data** | Medium | Weekly updates; show freshness in admin UI; allow manual refresh |
| **Cost estimation errors** | Medium | Use recent actual usage averages; allow user to override per-model cost |
| **Database corruption** | Medium | Checksums; versioned releases; easy rollback to previous version |
| **License incompatibility** | Low | Only store scores (facts), not benchmark problems; include attribution |
| **File size too large** | Low | Compress (gzipped ~2MB); incremental updates possible |
| **Remote backend latency** | High | Track real latency; penalize in routing; circuit breakers |
| **Rate limits from providers** | High | Token bucket rate limiting per backend; cascading fallback |

---

## FAQ

### Q: Why not just use OpenRouter directly?

A: SmarterRouter adds value beyond OpenRouter:
- **Local backends** (Ollama) for privacy/cost control
- **Intelligent routing** across multiple providers based on quality + cost + latency
- **Profiling** for local models to measure VRAM needs
- **Cache warming** and smart caching layers
- **Unified API** regardless of provider
- **Self-hosting** without relying on single aggregator

### Q: Will this increase costs?

A: No. The provider.db is free to download. You still pay provider prices directly. We don't take a cut.

### Q: What if a model isn't in provider.db?

A: Three options:
1. Show with default score (0.5) - user sees "unbenchmarked" badge
2. Allow user to add manual benchmarks via admin API
3. Profile locally (if it's a local model)

### Q: How is cost calculated?

A: We estimate per-request: `(input_tokens * prompt_cost) + (output_tokens * completion_cost)`. Input/output token counts come from recent usage patterns (averaged over last 100 requests) or user-provided defaults.

### Q: Can I use this with my own private models?

A: Yes! You can:
- Keep them as local backends (Ollama) and let SmarterRouter profile them
- Add them to provider.db manually with your own benchmark scores
- Use capability flags to indicate vision/tools

### Q: What if provider.db is outdated?

A: Router still works; just shows warning in logs. You can manually trigger refresh via `/admin/provider-db/refresh`. We recommend weekly updates.

### Q: How do I contribute new benchmark sources?

A: Fork the provider-data repo, add a new fetcher in `sources/`, submit PR. The build pipeline will incorporate it.

### Q: Does this replace HuggingFace/LMSYS sync?

A: No. Those syncs populate the local `ModelBenchmark` table for **local models**. The provider.db is for **remote models**. They coexist.

---

## Next Steps

1. **Decide on repository structure**: Separate `smarterrouter-provider-data` repo?
2. **Build MVP**: OpenRouter + Arena.ai + SWE-bench only (3 sources)
3. **Create GitHub Actions workflow** for weekly builds
4. **Implement BackendRegistry** in main codebase
5. **Write documentation** for users
6. **Beta test** with multi-backend users

---

**Document Version**: 1.0  
**Last Updated**: 2025-02-23  
**Status**: Proposed, awaiting approval
