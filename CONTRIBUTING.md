# Contributing to Provider Database

Thank you for your interest in improving the provider.db build system! This document provides guidelines for contributing.

## How to Contribute

### Reporting Bugs

If you find a bug or issue, please open a GitHub issue with:

1. **Clear description** of the problem
2. **Steps to reproduce** (if applicable)
3. **Expected vs actual behavior**
4. **Environment details** (OS, Python version, Docker version if used)
5. **Logs or error messages** (if any)

### Suggesting Features

Feature suggestions are welcome! Please:

1. Check existing issues and discussions to avoid duplicates
2. Provide a clear use case and rationale
3. Consider if it fits the project scope (automated benchmark aggregation for SmarterRouter)

### Submitting Changes

#### 1. Fork & Clone

```bash
git clone https://github.com/YOUR-USERNAME/provider.git
cd provider
git remote add upstream https://github.com/peva3/SmarterRouter-provider.git
```

#### 2. Create a Branch

```bash
git checkout -b my-feature-branch
```

#### 3. Make Changes

- Follow existing code style (PEP 8, type hints)
- Add tests for new functionality
- Update documentation as needed
- Keep changes focused and atomic

#### 4. Run Tests

```bash
pytest router/provider_db/tests/ -v
```

All tests must pass before submission.

#### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new benchmark source for X"
```

Use clear, concise commit messages. Consider conventional commits format.

#### 6. Push & Pull Request

```bash
git push origin my-feature-branch
```

Open a Pull Request on GitHub with:

- Description of changes
- Link to related issues
- Screenshots or output (if relevant)

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Build database locally
python -m router.provider_db.cli build --db-path data/provider.db

# Run tests
pytest router/provider_db/tests/ -v

# Validate database
python -m router.provider_db.cli validate --db-path data/provider.db

# Check health
python -m router.provider_db.cli health --db-path data/provider.db
```

### Code Guidelines

- **Type hints**: Required for all function signatures and class methods
- **Error handling**: Use try/except appropriately; log errors with context
- **Rate limiting**: Respect source APIs; use the `RateLimiter` utility
- **Validation**: Sanitize inputs; validate score ranges before DB insertion
- **Documentation**: Add docstrings to new functions and classes
- **Testing**: Aim for at least 80% coverage on new code

### Adding New Benchmark Sources

If you want to add a new benchmark source:

1. Create file `router/provider_db/sources/yoursource.py`
2. Implement `fetch_yoursource()` function returning `Dict[str, float]`
3. Add fallback data in `FALLBACK_SCORES` dictionary
4. Export in `sources/__init__.py`
5. Add to `builder.py`'s `_fetch_all_sources()` method
6. Update `README.md` and `docs/DEEPDIVE.md` with source details
7. Add tests in `tests/test_provider_db.py`

See existing sources for patterns.

### Database Migrations

If you modify the database schema:

1. Add migration logic to `ProviderDB._migrate_schema()`
2. Ensure backward compatibility with existing databases
3. Update this documentation
4. Test migration from previous schema

### Questions?

- **GitHub Discussions**: For general questions and ideas
- **GitHub Issues**: For bugs and feature requests
- **Security issues**: See [SECURITY.md](SECURITY.md) for responsible disclosure

---

Thank you for contributing to provider.db! Your work helps SmarterRouter make better routing decisions for the entire community.
