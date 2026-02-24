# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-24

### Added

#### Database Schema
- `model_benchmarks` table with columns: `model_id`, `reasoning_score`, `coding_score`, `general_score`, `elo_rating`, `last_updated`, `archived`
- `aliases` table for model name variations
- `metadata` table for build information
- Archive system to preserve historical model data

#### Benchmark Sources (14 new sources)
- **LiveCodeBench** - Continuous coding evaluation from LeetCode/AtCoder/Codeforces
- **FrontierMath** - Advanced research mathematics benchmark
- **AIME** - Competition math (AIME 2024/2025)
- **SciCode** - Research coding benchmark
- **MEGA-Bench** - 500+ real-world multimodal tasks
- **MixEval-X** - Any-to-any multimodal evaluation
- **GPQA** - Graduate-level science reasoning
- **StatEval** - Comprehensive statistics benchmark
- **Chinese benchmarks** - C-Eval, C-MMLU, Chinese-SimpleQA
- **Chinese reasoning, coding, and ELO estimation** - Enhanced Chinese model evaluation with specialized benchmarks
- **Tool Use benchmarks** - BFCL function calling
- **Vision benchmarks** - MMMU, MMBench multimodal
- **AILuminate** - AI risk/reliability benchmark
- **Domain-Specific** - Healthcare, Legal, Finance, Science
- **HELM** - Stanford holistic evaluation

#### Core Features
- **100% Model Coverage** - All 436 OpenRouter models have benchmark data
- **Heuristic Estimation** - Enhanced system to estimate scores for models without real benchmark data
- **Provider Baselines** - 45+ provider reputation baselines
- **Size-Based Heuristics** - Models by parameter count (405B, 70B, 30B, 13B, 7B, 3B, 1B)
- **Variant Detection** - Reasoning, coding, vision, search, guard variants
- **Incremental Updates** - Only updates changed models, preserves historical data
- **Auto-Archive** - Marks removed OpenRouter models as archived

#### Infrastructure
- **GitHub Actions Workflow** - Twice daily builds (10am/10pm EST)
- **CLI Commands**:
  - `build` - Build the database
  - `stats` - Show statistics
  - `health` - Check database health
  - `validate` - Validate for SmarterRouter compatibility
  - `inspect` - Inspect specific model

#### Reliability Features
- **Rate Limiter** - Configurable API call rate limiting
- **Retry with Backoff** - Exponential backoff for failed requests
- **Input Sanitization** - Model ID validation to prevent injection
- **Score Validation** - Range checking for all benchmark scores
- **ELO Validation** - Validates ELO ratings are within reasonable bounds

#### Testing
- **44 Unit Tests** - Comprehensive test coverage
- **Mock Tests** - For API fetcher testing
- **Integration Tests** - For database operations
- **Validation Tests** - For CLI commands

### Changed

#### Database
- Schema updated to include `archived` column
- Migration system added for schema changes
- Improved error handling for database operations

#### Builder
- Parallel fetching of all benchmark sources
- Better error handling with per-source tracking
- Added model estimation for unknown providers

#### CLI
- Added health check command
- Added validate command
- Improved stats output with sources list
- Added verbose logging support

### Fixed

- Fixed failing OpenRouterFetcher mock test
- Fixed model ID sanitization in database operations
- Fixed archived column migration for existing databases
- Fixed database path handling in CLI
- Fixed general_score default value (was 1000, now 0.0)
- Fixed empty result handling for all sources (now properly counted as failures)
- Fixed reactivation logic to use correct set of archived models
- Ensured stats consistency for added/estimated model counts
- Fixed write logic to always upsert existing models on every build (now updates scores instead of skipping)
- Fixed model_mapper.py: removed leading spaces in PROVIDER_PREFIXES keys, removed duplicate entries, and removed dangerous fuzzy matching that could mis-route models.
- Updated FALLBACK_ELO in lmsys_arena.py to ensure correct canonical IDs.

### Added

#### Dynamic Authority Weighting System
- **Tier-based Base Weights**: Sources weighted by reliability (Tier 1: 1.0, Tier 2: 0.9, Tier 3: 0.8)
- **Consensus-based Multipliers**: Correlation-based weighting that penalizes outliers
- **Weighted Averaging**: Final score = base_weight × consensus_multiplier × score
- Sources tracked through aggregation pipeline for full provenance

### Enhanced

- **Expanded data sources**: Now intelligently aggregates all 33 working benchmark sources (previously only 4). Sources are mapped to the 4 score categories:
  - **ELO**: LMSYS Arena + arena.ai (averaged)
  - **Reasoning**: LiveBench, GSM8K, ARC, BBH, AGIEval, MathVista, FrontierMath, AIME, StatEval, GPQA, MATH, HellaSwag (13 sources)
  - **Coding**: BigCodeBench, HumanEval, SWE-bench, Aider, LiveCodeBench, SciCode, Tool Use (8 sources)
  - **General**: MMLU, MMLU-Pro, MixEval-X, Chinese, AILuminate, MEGA-Bench, HELM, Domain-Specific, Vision, TruthfulQA, Safety, Multilingual (12 sources)
- **Multi-source averaging**: When multiple sources in the same category provide scores for a model, they are automatically averaged. This yields more robust, consensus-driven benchmark data.
- **Resilience**: If 1-2 sources go offline, category scores remain populated from remaining sources, ensuring high coverage.
- **Conflict resolution**: Sources with duplicate model entries within a category are averaged (not overridden).

### Documentation

- Comprehensive README.md with SmarterRouter compatibility
- AGENTS.md with technical specifications
- BUILD_STATUS.md with deployment status
- DELIVERABLE.md with project deliverables
- IMPLEMENTATION_PLAN.md with phased approach

---

## [1.1.0] - 2026-02-24

### Security Fixes

#### Critical Security Fixes
- **Fixed SQL injection vulnerability** in `database.py:155` - Changed from unsafe string formatting to parameterized query with tuple expansion
- **Enhanced input sanitization** - Improved `sanitize_model_id()` function to handle null bytes, control characters, and excessive length
- **Added comprehensive validation** - All scores validated for 0-100 range, ELO ratings validated for reasonable bounds

#### Schema Security
- **Simplified schema to match RouterEngine exactly** - Removed `archived` and `last_updated` columns that weren't part of router specification
- **Eliminated migration complexity** - Removed `_migrate_schema()` method and archive-related methods
- **Exact column matching** - Database now has exactly 5 columns: `model_id`, `reasoning_score`, `coding_score`, `general_score`, `elo_rating`

### Performance & Reliability

#### Rate Limiting
- **Added rate limiting decorator** - `@rate_limited` decorator applied to all source fetch functions
- **Configurable rate limits** - `RateLimiter` class allows tuning calls per second
- **Prevents API throttling** - Protects external APIs from being overwhelmed

#### Error Handling
- **Critical source failure handling** - Builder continues when LiveBench, BigCodeBench, MMLU, or LMSYS fail
- **Graceful degradation** - Missing critical source scores default to 0 (as router expects)
- **Detailed error tracking** - Sources tracked as attempted/succeeded/failed in statistics

#### Vision/Tool Capability Detection
- **Enhanced alias generation** - Models with vision/tool capabilities get keyword-enhanced aliases
- **RouterEngine compatibility** - Ensures model names contain required keywords for capability detection
- **Provider-specific patterns** - OpenAI models get `-vision` and `-tools` aliases when appropriate

### Configuration & Logging

#### Configuration Management
- **Added `config.yaml`** - Centralized configuration for API endpoints, rate limits, source priorities
- **Heuristic configuration** - Provider baselines, size modifiers, variant detection in config file
- **Build settings** - Parallelism, caching, validation settings configurable

#### Structured Logging
- **Added `logging_config.py`** - Structured logging with consistent message formats
- **Operation tracking** - Logs build start/complete, source fetch events, database writes
- **Security logging** - Logs SQL injection prevention, score validation failures
- **Configurable output** - Console and file logging with rotation

### Testing

#### New Test Suite
- **Added `test_fixes.py`** - 9 new tests covering security fixes and improvements
- **SQL injection tests** - Verifies parameterized queries prevent injection
- **Schema compatibility tests** - Ensures exact match with RouterEngine expectations
- **Rate limiting tests** - Validates rate limiter decorator functionality
- **Score validation tests** - Confirms 0-100 range enforcement

#### Updated Existing Tests
- **Fixed broken tests** - Updated tests for simplified schema (removed `last_updated`, `archived`)
- **Maintained 100% pass rate** - All 55 original tests pass, plus 9 new tests

### Code Quality

#### Architecture Improvements
- **Simplified database layer** - Removed archive functionality, migration complexity
- **Modular configuration** - Separated settings from code
- **Structured error handling** - Consistent error patterns across all sources
- **Type safety** - Improved type annotations and validation

#### Maintenance Benefits
- **Easier debugging** - Structured logging provides clear operation tracking
- **Simplified deployment** - Configuration file reduces environment-specific code
- **Better monitoring** - Rate limiting and error handling improve system observability
- **Reduced attack surface** - SQL injection fix eliminates critical vulnerability

### Compatibility Notes

#### SmarterRouter Integration
- **Schema exact match** - Database now matches RouterEngine expectations exactly
- **Keyword compatibility** - Vision/tool keyword aliases ensure proper capability detection
- **Score compatibility** - Validation ensures scores are in 0-100 range router expects
- **Error compatibility** - Missing scores default to 0 (router handles gracefully)

#### Breaking Changes
- **Archive functionality removed** - Models no longer marked as archived when removed from OpenRouter
- **Simplified schema** - `last_updated` and `archived` columns removed from database
- **Configuration required** - New `config.yaml` file needed for custom deployments

### Upgrade Instructions

1. **Backup existing database** - Schema changes may require rebuilding
2. **Add `config.yaml`** - Copy from example and customize as needed
3. **Update crontab** - No changes needed if using default configuration
4. **Monitor first build** - Check logs for any configuration issues
5. **Verify SmarterRouter integration** - Ensure router can query new schema

This release focuses on security, reliability, and maintainability while maintaining perfect compatibility with SmarterRouter's RouterEngine.

---

## [1.2.0] - 2026-02-24

### Added

#### New Benchmark Sources (5 new sources)
- **Hendrycks MATH** - Advanced mathematical reasoning benchmark with 12,500 competition-level problems
- **HellaSwag** - Commonsense reasoning benchmark testing sentence completion in natural contexts
- **TruthfulQA** - Factual accuracy benchmark measuring tendency to reproduce falsehoods
- **Safety benchmarks** - Harmful content refusal and alignment with safety guidelines
- **Multilingual benchmarks** - Enhanced C-Eval and C-MMLU support via HuggingFace datasets

#### Enhanced Coverage
- **Expanded model coverage** - Added scores for 112+ additional models from MATH benchmark dataset
- **Improved mapping** - Enhanced model name cleaning for MATH benchmark complex naming patterns
- **Better fallback data** - Comprehensive static scores for all new sources based on published results

#### Research Integration
- **Benchmark gap analysis** - Comprehensive analysis of 263 benchmark datasets on HuggingFace
- **Missing benchmarks identification** - Identified 248 benchmark datasets not currently covered
- **Strategic source selection** - Prioritized implementation based on model coverage and score availability

### Updated
- **Source count** - Increased from 28 to 33 benchmark sources
- **README documentation** - Updated source list and counts
- **Research files** - Updated existing sources list in analysis scripts

### Compatibility
- **SmarterRouter compatibility maintained** - All new sources integrate seamlessly with existing schema
- **Category mapping** - MATH and HellaSwag mapped to reasoning scores, TruthfulQA and Safety mapped to general scores
- **Score ranges** - All new sources produce 0-100 scale scores as required by RouterEngine

---

## [0.9.0] - 2026-02-23

### Added

- Initial database builder implementation
- Basic benchmark sources (LMSYS, LiveBench, BigCodeBench, MMLU)
- Model mapper for canonical ID resolution
- Basic CLI interface

---

## [0.8.0] - 2026-02-22

### Added

- Research phase completed
- Benchmark source analysis
- Provider coverage strategy
- Architecture design

---

## [0.1.0] - 2026-02-20

### Added

- Project initialization
- Requirements gathering
- SmarterRouter compatibility analysis
