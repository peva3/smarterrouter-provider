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

### Documentation

- Comprehensive README.md with SmarterRouter compatibility
- AGENTS.md with technical specifications
- BUILD_STATUS.md with deployment status
- DELIVERABLE.md with project deliverables
- IMPLEMENTATION_PLAN.md with phased approach

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
