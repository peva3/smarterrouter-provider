# Provider Database Builder - Docker Usage

## Quick Start

```bash
# 1. Build the Docker image
docker build -t provider-db-builder .

# 2. Run the build (mounts ./data to persist output)
mkdir -p data
docker run --rm -v $(pwd)/data:/app/data provider-db-builder

# 3. Output is in ./data/provider.db
ls -lh data/
```

## With API Key (recommended for OpenRouter rate limits)

```bash
export OPENROUTER_API_KEY=sk-your-key-here
docker run --rm \
  -v $(pwd)/data:/app/data \
  -e OPENROUTER_API_KEY \
  provider-db-builder
```

## Using the Helper Script

```bash
# Build image
./docker-build.sh image

# Build database (uses existing image)
./docker-build.sh build ./data

# Or with API key
OPENROUTER_API_KEY=sk-xxx ./docker-build.sh build

# Open shell in container for debugging
./docker-build.sh shell
```

## Docker Compose

```bash
# One-off build
docker-compose run --rm build

# With API key
OPENROUTER_API_KEY=sk-xxx docker-compose run --rm build

# Start scheduler (continuous)
docker-compose up -d scheduler
```

## What's Inside

- **Base**: python:3.11-slim (~120MB)
- **Dependencies**: aiohttp, pydantic, beautifulsoup4, datasets, etc.
- **Entrypoint**: `python -m router.provider_db build -o /app/data/provider.db`
- **Volumes**: Mount `./data` to persist the database
- **Arch**: Linux amd64 (buildx for multi-arch if needed)

## Production Deployment

For scheduled production builds, push the image to a registry:

```bash
# Tag and push
docker tag provider-db-builder yourorg/provider-db-builder:latest
docker push yourorg/provider-db-builder:latest

# Run in CI/CD or cron
docker run --rm -v /path/to/storage:/app/data -e OPENROUTER_API_KEY yourorg/provider-db-builder:latest
```

## GitHub Actions Integration

```yaml
- name: Build with Docker
  run: |
    docker build -t provider-db-builder .
    mkdir -p data
    docker run --rm \
      -v ${{ github.workspace }}/data:/app/data \
      -e OPENROUTER_API_KEY="${{ secrets.OPENROUTER_API_KEY }}" \
      provider-db-builder
```

## Customization

- Edit `Dockerfile` to add system packages
- Modify `CMD` in Dockerfile for different default arguments
- Use `--build-arg` to pass build-time arguments
- Set `SCHEDULE_INTERVAL` env var for continuous builds (compose)

## Troubleshooting

**Out of memory**: HF datasets are large (~1GB). Increase Docker memory limit:
```bash
docker run --memory-swap=4g ...
```

**Slow builds**: First build downloads datasets; subsequent builds are faster (cached in layer).

**Permission errors**: Ensure host `data/` directory is writable:
```bash
mkdir -p data && chmod 755 data
```
