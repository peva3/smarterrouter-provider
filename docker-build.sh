#!/bin/bash
# Docker build and run helper script

set -e

IMAGE_NAME="smarterrouter/provider-db-builder"
TAG="latest"

# Build the Docker image
build_image() {
    echo "Building Docker image..."
    docker build -t $IMAGE_NAME:$TAG .
    echo "✓ Image built: $IMAGE_NAME:$TAG"
}

# Run the builder
run_build() {
    local output_dir="${1:-./data}"
    local api_key="${OPENROUTER_API_KEY:-}"
    
    echo "Starting provider.db build in Docker..."
    echo "Output directory: $output_dir"
    
    # Create output directory if needed
    mkdir -p "$output_dir"
    
    # Run container
    docker run --rm \
        -v "$(pwd)/$output_dir:/app/data" \
        ${api_key:+-e OPENROUTER_API_KEY="$api_key"} \
        $IMAGE_NAME:$TAG
    
    echo "✓ Build complete. Database at: $output_dir/provider.db"
}

# Interactive shell
shell() {
    docker run --rm -it \
        -v "$(pwd):/app" \
        -v "$(pwd)/data:/app/data" \
        ${OPENROUTER_API_KEY:+-e OPENROUTER_API_KEY="$OPENROUTER_API_KEY"} \
        $IMAGE_NAME:$TAG /bin/bash
}

# Help
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build [output_dir]    Build provider.db (default: ./data)"
    echo "  shell                Open bash shell in container"
    echo "  image                Build Docker image only"
    echo "  help                 Show this message"
    echo ""
    echo "Examples:"
    echo "  $0 build ./data"
    echo "  OPENROUTER_API_KEY=sk-xxx $0 build"
    echo "  $0 shell"
}

case "${1:-help}" in
    build)
        run_build "${2:-./data}"
        ;;
    image)
        build_image
        ;;
    shell)
        shell
        ;;
    *)
        usage
        ;;
esac
