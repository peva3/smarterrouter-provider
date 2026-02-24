# Provider Database for SmarterRouter

**Builds `provider.db` - a comprehensive benchmark database that powers intelligent model routing in SmarterRouter.**

This project automatically collects benchmark scores from 33+ sources, applies intelligent heuristics for uncovered models, and produces a SQLite database with **100% coverage** of all OpenRouter models. The database integrates seamlessly with SmarterRouter's RouterEngine to enable automatic model selection based on reasoning, coding, and general knowledge capabilities.

## ✨ Features

- **100% Model Coverage** - All 436+ OpenRouter models have benchmark data
- **Real + Estimated Scores** - 74% real benchmarks + 26% intelligent heuristics
- **SmarterRouter Compatible** - Exact schema match: `model_id`, `reasoning_score`, `coding_score`, `general_score`, `elo_rating`
- **Dynamic Authority Weighting** - Sources weighted by tier (Tier 1: 1.0, Tier 2: 0.9, Tier 3: 0.8) with consensus-based outlier penalization
- **Security Hardened** - SQL injection protection, input validation, rate limiting
- **Vision/Tool Keyword Support** - Automatic alias generation for capability detection
- **Configuration Driven** - YAML configuration for API endpoints, rate limits, heuristics
- **Structured Logging** - Comprehensive logging with operation tracking
- **Docker Ready** - Single-command build with all dependencies included
- **Automated Scheduling** - Crontab examples for twice-daily updates (10am/10pm EST)
- **Production Grade** - 64 passing tests, validation commands, health checks

## 🚀 Quick Start

```bash
# Build Docker image
docker build -t provider-db-builder .

# Generate database
mkdir -p data
docker run --rm -v $(pwd)/data:/app/data provider-db-builder:latest

# Validate for SmarterRouter
python -m router.provider_db.cli validate --db-path data/provider.db
```

## 📊 Coverage

| Metric | Value |
|--------|-------|
| Total OpenRouter Models | 436 |
| With Real Benchmarks | 324 (74%) |
| With Heuristics | 112 (26%) |
| ELO Range | 1010-1505 |
| Score Range | 0-100 (all validated) |
| Test Coverage | 64 tests passing |
| Security Fixes | SQL injection, input validation, rate limiting |

## 🔧 CLI Commands

```bash
python -m router.provider_db.cli build      # Build database
python -m router.provider_db.cli stats      # Show statistics
python -m router.provider_db.cli health     # Check health
python -m router.provider_db.cli validate   # SmarterRouter compatibility
python -m router.provider_db.cli inspect <model_id>  # View model scores
```

## 📦 What's Inside

**33 Benchmark Sources** including:
- **LMSYS Chatbot Arena** (ELO)
- **LiveBench** (reasoning)
- **BigCodeBench** (coding)
- **MMLU** (general knowledge)
- **SWE-bench, Aider, HumanEval** (coding variants)
- **GSM8K, ARC, BBH, MathVista, AGIEval** (reasoning variants)
- **FrontierMath, AIME, SciCode** (advanced math/coding)
- **MEGA-Bench, MixEval-X** (multimodal)
- **Chinese benchmarks, Tool Use, Vision**
- **AILuminate, Domain-Specific, HELM**
- **Hendrycks MATH** (advanced math reasoning)
- **HellaSwag** (commonsense reasoning)
- **TruthfulQA** (factual accuracy)
- **Safety benchmarks** (harmful content refusal)
- **Multilingual benchmarks** (C-Eval, C-MMLU)

**Smart Heuristics**:
- 45+ provider baselines (OpenAI, Anthropic, Meta, etc.)
- Size-based modifiers (405B, 70B, 30B, 13B, 7B, 3B, 1B)
- Variant detection (reasoning, coding, vision, search, guard)
- Category detection (search engines, research models, safety models)

**Security & Reliability**:
- SQL injection protection with parameterized queries
- Input validation and sanitization
- Rate limiting for API calls
- Critical source error handling
- Structured logging and monitoring

## 🔄 Integration with SmarterRouter

1. Build `provider.db` using Docker
2. Copy to SmarterRouter's data directory
3. SmarterRouter automatically queries benchmark scores
4. Router applies formula: `(benchmark × 1.5 × Q) + (elo × 1.0 × Q) + (profile × 0.8 × Q) + (inference × 0.4 × Q)`
5. Models selected based on capability + hardware profile + user preferences

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OpenRouter API │────▶│  33 Benchmark    │────▶│   Heuristic     │
│  (model list)   │     │   Sources        │     │   Estimator    │└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ SmarterRouter   │◀────│  provider.db     │◀────│   Builder      │
│  RouterEngine   │     │  (SQLite)        │     │   (Docker)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 📁 Repository Structure

```
provider/
├── Dockerfile                  # Builds provider-db-builder image
├── requirements.txt            # Python dependencies
├── config.yaml                 # Configuration file (API endpoints, rate limits)
├── data/                       # Output directory for provider.db (generated)
├── router/provider_db/
│   ├── builder.py              # Main orchestration
│   ├── database.py             # SQLite operations (security hardened)
│   ├── models.py               # Pydantic schemas
│   ├── model_mapper.py         # Name → canonical ID
│   ├── cli.py                  # Command-line interface
│   ├── utils.py                # Utilities (rate limiting, validation)
│   ├── logging_config.py       # Structured logging configuration
│   ├── sources/                # 33 benchmark fetchers
│   └── tests/                  # Test suite (64 tests)
└── docs/                       # Documentation
    ├── DEEPDIVE.md             # Technical deep dive (consolidated)
    └── CRONTAB_EXAMPLE.txt     # Automation examples
```

## 🧪 Testing

```bash
pytest router/provider_db/tests/ -v
# 64 tests passing (55 original + 9 security/feature tests)

# Run security-focused tests
pytest router/provider_db/tests/test_fixes.py -v
```

## 📝 License

MIT - see LICENSE file

## 🔒 Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Perfect for:** SmarterRouter users, AI infrastructure teams, and anyone wanting automatic model selection based on capability metrics. The database is generated twice daily and committed to GitHub for easy consumption.
