#!/bin/bash
# Daily AI News Agent run script
# Runs crawl + digest and logs output

set -e

PROJECT_DIR="/home/ubuntu/ai-news-agent"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/digest_$(date +%Y%m%d_%H%M%S).log"

cd "$PROJECT_DIR"

# Create logs dir if needed
mkdir -p "$LOG_DIR"

# Activate virtual environment and run
{
    echo "=== AI News Digest - $(date) ==="
    echo ""

    echo "Crawling sources..."
    uv run news crawl

    echo ""
    echo "Generating and sending digest..."
    uv run news digest

    echo ""
    echo "=== Complete ==="
} 2>&1 | tee "$LOG_FILE"
