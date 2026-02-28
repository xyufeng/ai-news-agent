#!/bin/bash
# Deploy to EC2

set -e

EC2_HOST="ubuntu@your-ec2-host"  # Change this
REMOTE_DIR="/home/ubuntu/ai-news-agent"

# Sync code (exclude unnecessary files)
rsync -avz --progress \
    --exclude '.venv' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'news.db' \
    --exclude 'logs' \
    --exclude 'uv.lock' \
    ./ "$EC2_HOST:$REMOTE_DIR"

# Run remote commands
ssh "$EC2_HOST" << 'EOF'
cd /home/ubuntu/ai-news-agent
uv sync
sudo systemctl restart ai-news-dashboard
echo "Deployed and restarted service"
EOF

echo "Deploy complete!"
