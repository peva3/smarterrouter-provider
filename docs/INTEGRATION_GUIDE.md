# Integration Guide: Merging provider.db with SmarterRouter

This guide explains how to integrate `provider.db` (containing external benchmark data) with SmarterRouter's local `router.db`.

## The Challenge

SmarterRouter's local database (`router.db`) typically uses `ollama_name` as the primary key for models (e.g., `llama3`). 
However, external providers like OpenRouter use `model_id` (e.g., `meta-llama/llama-3-8b`).

To route effectively between local and external models, we bridge this gap in two ways:

1. **Compatibility View**: `provider.db` now exposes a `router_compatibility_view` that aliases `model_id` as `ollama_name`.
2. **Merge Script**: A utility to copy benchmark data from `provider.db` into `router.db`.

## Method 1: Using the Merge Script (Recommended)

This method copies the high-quality benchmark data from `provider.db` directly into your local `router.db`.

1. **Build provider.db** (if you haven't already):
   ```bash
   python -m router.provider_db.cli build --db-path data/provider.db
   ```

2. **Run the export script**:
   ```bash
   python -m router.provider_db.export \
     --provider-db data/provider.db \
     --router-db /path/to/smarterrouter/data/router.db
   ```

   **Options:**
   - `--dry-run`: Preview changes without writing.

   **What happens:**
   - Active models from `provider.db` are inserted into `router.db`.
   - `model_id` is mapped to `ollama_name`.
   - Existing records are updated with fresh scores.

## Method 2: Direct Attachment (Advanced)

If you modify SmarterRouter to support attached databases, you can query `provider.db` directly.

1. **Attach Database**:
   ```sql
   ATTACH DATABASE 'path/to/provider.db' AS provider;
   ```

2. **Query via Compatibility View**:
   ```sql
   SELECT * FROM provider.router_compatibility_view 
   WHERE ollama_name = 'openai/gpt-4-turbo';
   ```

   The view automatically maps columns to match SmarterRouter's expectations:
   - `model_id` → `ollama_name`
   - `reasoning_score` → `reasoning_score`
   - etc.

## Enabling Multi-Backend Routing

To fully utilize external models, SmarterRouter needs a `BackendRegistry`. We have provided a reference implementation in `router/backends/registry.py`.

**Steps to Integrate:**

1. Copy `router/backends/registry.py` to your SmarterRouter codebase.
2. Implement specific backends (e.g., `OpenRouterBackend` using `aiohttp`).
3. Update `RouterEngine` to use `BackendRegistry.get_backend_for_model(model_id)`.

**Example Logic:**

```python
# In RouterEngine.route()
backend = self.backend_registry.get_backend_for_model(selected_model_id)
response = await backend.chat(model=selected_model_id, messages=messages)
```

## Schema Mapping

| Concept | provider.db Column | SmarterRouter Column | Notes |
|---------|-------------------|----------------------|-------|
| Identifier | `model_id` | `ollama_name` | Mapped via view/script |
| Reasoning | `reasoning_score` | `reasoning_score` | 0-100 scale matches |
| Coding | `coding_score` | `coding_score` | 0-100 scale matches |
| General | `general_score` | `general_score` | 0-100 scale matches |
| ELO | `elo_rating` | `elo_rating` | Raw 1000+ scale matches |

---

**Note**: `provider.db` preserves historical data via the `archived` column. The export script automatically filters out archived models to keep your router clean.
