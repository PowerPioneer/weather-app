#!/bin/bash
# Deployment script for Where to Go for Great Weather
# This script automates the deployment process: pull code, install dependencies,
# warm cache, and restart the service

set -e  # Exit on error

echo "🚀 Starting deployment..."
echo ""

# Pull latest code from git
echo "📥 Pulling latest changes from git..."
git pull origin main
echo ""

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate
echo ""

# Install/update dependencies
echo "📦 Installing/updating dependencies..."
pip install -r requirements-server.txt
echo ""

# Warm Redis cache (if Redis is available)
echo "🔥 Warming Redis cache..."
if python scripts/warm_cache.py; then
    echo "✅ Cache warming completed successfully"
else
    echo "⚠️  Cache warming skipped (Redis not available or error occurred)"
fi
echo ""

# Restart the systemd service
echo "🔄 Restarting weather-app service..."
sudo systemctl restart weather-app
echo ""

# Wait a moment for service to start
sleep 2

# Check if service is running
echo "🔍 Checking service status..."
if systemctl is-active --quiet weather-app; then
    echo "✅ Deployment successful! Service is running."
    echo ""
    echo "📊 Service status:"
    sudo systemctl status weather-app --no-pager -l
else
    echo "❌ Deployment failed! Service is not running."
    echo ""
    echo "📊 Service status:"
    sudo systemctl status weather-app --no-pager -l
    exit 1
fi

echo ""
echo "✨ Deployment complete!"
echo "🌐 Your app is now running with the latest changes."
