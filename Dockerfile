FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for HF datasets and SSL
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for output
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
ENTRYPOINT ["python", "-m", "router.provider_db"]
CMD ["build", "-o", "/app/data/provider.db"]
