# Build and usage status

## Completed Components

### Phase 1: Provider Database (router/provider_db/)
✓ models.py - Pydantic schemas (ModelInfo, BenchmarkRecord, AliasRecord, Metadata)
✓ database.py - ProviderDB class with SQLite operations (CRUD, indexes)
✓ sources/openrouter.py - OpenRouter API fetcher (async, with pricing)
✓ sources/arena.py - Arena.ai HTML scraper (basic)
✓ sources/swe_bench.py - SWE-bench HuggingFace fetcher
✓ sources/livecodebench.py - LiveCodeBench HF fetcher
✓ sources/evalplus.py - EvalPlus HF fetcher
✓ sources/cruxeval.py - CRUXEval HF fetcher
✓ normalizer.py - Score normalization (min-max) and composite calculation (0.4/0.3/0.3 weights)
✓ builder.py - Orchestration: fetch all sources → normalize → write DB → generate aliases
✓ cli.py - Command: `python -m router.provider_db build -o data/provider.db`
✓ __init__.py - Package exports

**Status**: Stubs are functional but need real API access and HF datasets for production data.

### Phase 2: Backend Registry & Integration
✓ router/backends/base.py - LLMBackend protocol + ModelInfo
✓ router/backends/ollama.py - Local Ollama backend implementation
✓ router/backends/openai.py - OpenAI-compatible remote backend
✓ router/backends/circuit_breaker.py - Circuit breaker with health states
✓ router/backends/__init__.py - BackendRegistry class (register, list_models, get_backend, health tracking, latency)
✓ router/config.py - Settings class with all new config options
✓ router/benchmark_db.py - BenchmarkDB wrapper (local + provider.db)
✓ router/vram_manager.py - Stub (skips VRAM for remote)
✓ router/router.py - RouterEngine with model selection, cost/latency penalties
✓ main.py - App startup: download provider.db, init registry, register backends
✓ router/__init__.py - Package init

**Status**: Core architecture complete. Integration points are defined.

## Missing/Partial

- **Real HF dataset parsing**: Current HF fetchers assume specific dataset structures; need actual inspection.
- **Arena.ai scraper**: Basic table parsing; real site HTML unknown.
- **VF model ID mapping**: Alias generation is basic; needs comprehensive mapping table.
- **Admin endpoints**: Not implemented (Phase 3).
- **Tests**: None written (Phase 4).
- **Profiler integration**: Local profiling bypass mentioned but not implemented.
- **Requirements**: requirements.txt created, but actual package versions may need adjustment.
- **VRAM manager**: Stub only; actual VRAM tracking not needed for this MVP.

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build provider.db (requires external dependencies, may fail without API keys/network):
   ```bash
   python -m router.provider_db build -o data/provider.db
   ```

3. Run main (stub mode, expects Ollama on localhost:11434):
   ```bash
   ROUTER_EXTERNAL_PROVIDERS=false python main.py
   ```

## Notes

- LSP errors in sources/* are due to missing packages (aiohttp, bs4, datasets). Install with requirements.txt to resolve.
- Code is syntactically valid Python, just missing deps.
- Architecture follows AGENTS.md spec closely.
